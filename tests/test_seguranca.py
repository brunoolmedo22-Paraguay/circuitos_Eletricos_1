"""Teste D — segurança, autenticação, permissões e concorrência."""

from __future__ import annotations

import pytest
import sqlalchemy as sa

from resolucoes import constants as C
from resolucoes import db
from resolucoes.errors import AuthError, ConflictError, NotFound, PermissionDenied, ValidationError

from conftest import ALL_REQ, BOOT, GOOD_CRITERIA, YOUTUBE, fill_and_submit, make_pdf, row_version


def test_bootstrap_exige_token_e_so_funciona_uma_vez(platform):
    p = platform
    assert p.users.bootstrap_needed()
    with pytest.raises(PermissionDenied):
        p.users.bootstrap_admin("token-errado", login="x", full_name="Invasor", email=None, password="Senha12345")
    p.users.bootstrap_admin(BOOT, login="monitor", full_name="Monitor", email=None, password="Senha12345")
    with pytest.raises(ConflictError):
        p.users.bootstrap_admin(BOOT, login="outro", full_name="Outro", email=None, password="Senha12345")
    assert not p.users.bootstrap_needed()


def test_login_sessao_e_sem_bloqueio(platform, actors):
    p = platform
    user, token = p.users.login("ANA ", "AnaSenha123")  # login normalizado
    assert user.login == "ana"
    assert p.users.resolve_session(token).id == user.id
    assert p.users.resolve_session("token-forjado") is None
    p.users.logout(token, user)
    assert p.users.resolve_session(token) is None

    with pytest.raises(AuthError) as e1:
        p.users.login("ana", "errada")
    with pytest.raises(AuthError) as e2:
        p.users.login("ninguem", "errada")
    assert e1.value.message == e2.value.message  # não revela se o login existe
    for _ in range(20):  # muitas tentativas erradas nunca bloqueiam a conta
        with pytest.raises(AuthError):
            p.users.login("ana", "errada")
    assert p.users.login("ana", "AnaSenha123")[0].login == "ana"


def test_senhas_nunca_aparecem_nos_logs(platform, actors):
    p = platform
    with pytest.raises(AuthError):
        p.users.login("ana", "SenhaSecreta999")
    p.users.login("beto", "BetoSenha123")
    with p.engine.connect() as conn:
        dump = " ".join(str(tuple(r)) for r in conn.execute(sa.select(db.audit_log)))
    assert "SenhaSecreta999" not in dump and "BetoSenha123" not in dump and "scrypt$" not in dump


def test_visitante_e_aluno_nao_acessam_administracao(platform, actors, exercise):
    p, ana = platform, actors["ana"]
    sid = fill_and_submit(p, ana, exercise)
    for actor in (None, ana):
        with pytest.raises(PermissionDenied):
            p.reviews.claim(actor, sid, expected_row_version=row_version(p, sid))
        with pytest.raises(PermissionDenied):
            p.reviews.approve(actor, sid, expected_row_version=row_version(p, sid), level=C.EXCELENTE,
                              requirements=ALL_REQ, criteria=GOOD_CRITERIA)
        with pytest.raises(PermissionDenied):
            p.reviews.inbox(actor)
        with pytest.raises(PermissionDenied):
            p.users.list(actor)
        with pytest.raises(PermissionDenied):
            p.admin.logs(actor)
        with pytest.raises(PermissionDenied):
            p.admin.export_backup(actor)
        with pytest.raises(PermissionDenied):
            p.exercises.create(actor, code="9.99", title="x", statement="y", unit="z")


def test_aluno_nao_altera_proprio_perfil_de_acesso(platform, actors):
    p, ana = platform, actors["ana"]
    with pytest.raises(PermissionDenied):
        p.users.set_role(ana, ana.id, C.ROLE_ADMIN)
    # Mesmo editando o próprio cadastro, campos protegidos são ignorados.
    u = p.users.update_profile(ana, ana.id, full_name="Outro Nome", matricula="999", login="admin", phone="+5545999998888")
    assert u.full_name == "Ana Souza" and u.matricula == "2024001" and u.login == "ana" and u.role == C.ROLE_ALUNO
    assert u.phone == "+5545999998888"


def test_aluno_nao_altera_nem_le_entrega_de_outro(platform, actors, exercise):
    p, ana, beto = platform, actors["ana"], actors["beto"]
    sid = p.submissions.start(ana, exercise.id)
    p.submissions.save_draft(ana, sid, expected_row_version=row_version(p, sid), pdf_bytes=make_pdf(), pdf_name="a.pdf")
    with pytest.raises(PermissionDenied):
        p.submissions.save_draft(beto, sid, expected_row_version=row_version(p, sid), youtube_url=YOUTUBE)
    with pytest.raises(PermissionDenied):
        p.submissions.submit(beto, sid, expected_row_version=row_version(p, sid), declaration=True)
    with pytest.raises(NotFound):
        p.submissions.detail(beto, sid)
    vid = p.submissions.detail(ana, sid)["current"]["id"]
    with pytest.raises(NotFound):
        p.submissions.version_pdf(beto, vid)
    with pytest.raises(NotFound):
        p.submissions.version_pdf(None, vid)
    assert p.submissions.version_pdf(ana, vid)[0].startswith(b"%PDF")


def test_parecer_e_privado(platform, actors, exercise):
    p, monitor = platform, actors["monitor"]
    sid = fill_and_submit(p, actors["ana"], exercise)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    rid = p.reviews.return_for_correction(monitor, sid, expected_row_version=row_version(p, sid),
                                          requirements=ALL_REQ, criteria=GOOD_CRITERIA,
                                          problems="Faltou justificar a escolha das malhas.")
    with pytest.raises(NotFound):
        p.reviews.parecer_pdf(actors["beto"], rid)
    with pytest.raises(PermissionDenied):
        p.reviews.parecer_pdf(None, rid)
    assert p.reviews.parecer_pdf(actors["prof"], rid)[0].startswith(b"%PDF")
    assert p.catalog.published() == []  # devolvida nunca aparece como aprovada


def test_ultimo_administrador_protegido(platform, actors):
    p, monitor, prof = platform, actors["monitor"], actors["prof"]
    p.users.set_role(monitor, prof.id, C.ROLE_ALUNO)
    with pytest.raises(ConflictError):
        p.users.set_role(monitor, monitor.id, C.ROLE_ALUNO)
    with pytest.raises(ConflictError):
        p.users.set_active(monitor, monitor.id, False)


def test_revogacao_de_perfil_tem_efeito_imediato(platform, actors):
    p, monitor, prof = platform, actors["monitor"], actors["prof"]
    user, token = p.users.login("professor", "Professora2026")
    assert p.users.resolve_session(token).is_admin
    p.users.set_role(monitor, prof.id, C.ROLE_ALUNO)
    assert p.users.resolve_session(token) is None  # sessões encerradas


def test_dois_admins_na_mesma_entrega(platform, actors, exercise):
    p, monitor, prof = platform, actors["monitor"], actors["prof"]
    sid = fill_and_submit(p, actors["ana"], exercise)
    rv = row_version(p, sid)
    p.reviews.claim(monitor, sid, expected_row_version=rv)
    with pytest.raises(ConflictError):  # visão desatualizada
        p.reviews.claim(prof, sid, expected_row_version=rv)
    with pytest.raises(ConflictError):  # sem assumir explicitamente
        p.reviews.claim(prof, sid, expected_row_version=row_version(p, sid))
    with pytest.raises(ConflictError):  # quem não iniciou não decide
        p.reviews.approve(prof, sid, expected_row_version=row_version(p, sid), level=C.BOM,
                          requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    stale = row_version(p, sid)
    p.reviews.claim(prof, sid, expected_row_version=stale, takeover=True)
    with pytest.raises(ConflictError):  # o monitor perdeu a análise
        p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level=C.BOM,
                          requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    p.reviews.approve(prof, sid, expected_row_version=row_version(p, sid), level=C.BOM,
                      requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    assert len(p.reviews.history(monitor)) == 1


def test_envio_duplicado_e_bloqueado(platform, actors, exercise):
    p, ana = platform, actors["ana"]
    sid = p.submissions.start(ana, exercise.id)
    assert p.submissions.start(ana, exercise.id) == sid  # sem submissões duplicadas
    from conftest import FALSTAD

    p.submissions.save_draft(ana, sid, expected_row_version=row_version(p, sid), youtube_url=YOUTUBE,
                             falstad_url=FALSTAD, duration_text="5:00", pdf_bytes=make_pdf(), pdf_name="a.pdf")
    rv = row_version(p, sid)
    p.submissions.submit(ana, sid, expected_row_version=rv, declaration=True)
    with pytest.raises(ConflictError):
        p.submissions.submit(ana, sid, expected_row_version=rv, declaration=True)
    with p.engine.connect() as conn:
        n = conn.execute(sa.select(sa.func.count()).select_from(db.versions).where(db.versions.c.submission_id == sid)).scalar_one()
    assert n == 1


def test_video_privado_ou_inexistente_bloqueia_envio(platform, actors, exercise):
    from conftest import FALSTAD

    p, ana = platform, actors["ana"]
    p.fake_youtube.status["PRIVADO1234"] = 401
    p.fake_youtube.status["REMOVIDO123"] = 404
    sid = p.submissions.start(ana, exercise.id)
    for vid, word in (("PRIVADO1234", "Privado"), ("REMOVIDO123", "não encontrou")):
        p.submissions.save_draft(ana, sid, expected_row_version=row_version(p, sid), youtube_url=f"https://youtu.be/{vid}",
                                 falstad_url=FALSTAD, duration_text="5:00", pdf_bytes=make_pdf(), pdf_name="a.pdf")
        with pytest.raises(ValidationError) as exc:
            p.submissions.submit(ana, sid, expected_row_version=row_version(p, sid), declaration=True)
        assert word in exc.value.message
    assert p.submissions.detail(ana, sid)["submission"]["status"] == C.RASCUNHO


def test_youtube_fora_do_ar_nao_bloqueia_mas_sinaliza(platform, actors, exercise):
    p, ana = platform, actors["ana"]

    def offline(*a, **k):
        raise ConnectionError("sem rede")

    p.http_get = offline
    sid = fill_and_submit(p, ana, exercise)
    cur = p.submissions.detail(ana, sid)["current"]
    assert cur["video_check"] == C.VIDEO_NAO_VERIFICADO and cur["state"] == C.V_ENVIADA


def test_rls_ativo_no_postgres(platform):
    """No Supabase, a API REST automática não deve ler as tabelas do módulo."""
    if platform.engine.dialect.name != "postgresql":
        pytest.skip("RLS só se aplica ao PostgreSQL")
    with platform.engine.connect() as conn:
        rows = conn.execute(sa.text(
            "SELECT relname, relrowsecurity FROM pg_class WHERE relname LIKE 'ce1_%' AND relkind = 'r'"
        )).all()
    assert rows and all(r[1] for r in rows), rows
