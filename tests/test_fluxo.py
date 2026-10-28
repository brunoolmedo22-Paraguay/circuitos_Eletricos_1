"""Testes A, B, C e critérios de aceitação 1–9 (camada de serviços)."""

from __future__ import annotations

import sqlalchemy as sa
from pypdf import PdfReader
import io

from resolucoes import constants as C
from resolucoes import db
from resolucoes.services.catalog import filter_items, group_by_exercise

from conftest import ALL_REQ, FALSTAD, GOOD_CRITERIA, YOUTUBE, fill_and_submit, make_pdf, row_version


def test_fluxo_completo_criterios_de_aceitacao(platform, actors, exercise):
    p = platform
    monitor, prof, ana = actors["monitor"], actors["prof"], actors["ana"]

    # PRIMEIRO — administrador cria 2.04 (fixture). Aluno vê nos Propostos.
    propostos = p.exercises.list(ana)
    assert [e.code for e in propostos] == ["2.04"]

    # SEGUNDO/TERCEIRO — aluno entrega os três materiais; fica pendente.
    sid = fill_and_submit(p, ana, exercise)
    det = p.submissions.detail(ana, sid)
    assert det["submission"]["status"] == C.SUBMETIDA
    assert det["current"]["state"] == C.V_ENVIADA
    assert det["current"]["youtube_id"] == "dQw4w9WgXcQ"
    assert det["current"]["falstad_url"] == FALSTAD  # link preservado byte a byte
    assert det["current"]["video_check"] == C.VIDEO_OK
    assert p.catalog.published() == []

    # QUARTO — administrador consulta os materiais e devolve com indicações.
    inbox = p.reviews.inbox(monitor, statuses=list(C.PENDING_STATUSES))
    assert [r["id"] for r in inbox] == [sid]
    pdf_bytes, _ = p.submissions.version_pdf(monitor, det["current"]["id"])
    assert pdf_bytes.startswith(b"%PDF")
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    crit = dict(GOOD_CRITERIA)
    crit["calculos"] = {"rating": C.RATING_NAO_ATENDE, "comment": "Sinal de I2 invertido na malha 2."}
    rid1 = p.reviews.return_for_correction(
        monitor, sid, expected_row_version=row_version(p, sid), requirements=ALL_REQ, criteria=crit,
        problems="A equação da malha 2 tem o sinal da fonte invertido.",
        recommendations="Refaça a LKT na malha 2 e confira no Falstad.",
    )

    # QUINTO — parecer gerado e acessível ao aluno.
    det = p.submissions.detail(ana, sid)
    assert det["submission"]["status"] == C.DEVOLVIDA
    parecer, nome = p.reviews.parecer_pdf(ana, rid1)
    text = "".join(pg.extract_text() for pg in PdfReader(io.BytesIO(parecer)).pages)
    assert "DEVOLVIDO PARA CORREÇÃO" in text
    assert "Ana Souza" in text and "2.04" in text and "Monitor da Disciplina" in text
    assert "Devolucao" in nome
    assert p.catalog.published() == []

    # SEXTO — aluno corrige e reenvia sem perder o histórico.
    p.submissions.new_version(ana, sid, expected_row_version=row_version(p, sid))
    p.submissions.save_draft(
        ana, sid, expected_row_version=row_version(p, sid), youtube_url="https://www.youtube.com/watch?v=abcdefghijk",
        falstad_url=FALSTAD, duration_text="7:10", pdf_bytes=make_pdf("v2 corrigida"), pdf_name="v2.pdf",
    )
    p.submissions.submit(ana, sid, expected_row_version=row_version(p, sid), declaration=True)
    det = p.submissions.detail(ana, sid)
    assert det["submission"]["status"] == C.REENVIADA
    assert [v["state"] for v in det["versions"]] == [C.V_DEVOLVIDA, C.V_ENVIADA]
    assert det["versions"][0]["youtube_id"] == "dQw4w9WgXcQ"  # v1 intacta
    assert len(det["reviews"]) == 1

    # SÉTIMO — segundo administrador revisa e aprova com MUITO BOM.
    p.reviews.claim(prof, sid, expected_row_version=row_version(p, sid))
    p.reviews.approve(prof, sid, expected_row_version=row_version(p, sid), level=C.MUITO_BOM,
                      requirements=ALL_REQ, criteria=GOOD_CRITERIA, observations="Boa explicação.",
                      verified_duration="7:10")

    # OITAVO — aparece no catálogo com miniatura, título, autor e nível.
    items = p.catalog.published()
    assert len(items) == 1
    it = items[0]
    assert it["code"] == "2.04" and it["title"] == "Análise de Malhas"
    assert it["author_name"] == "Ana Souza" and it["level"] == C.MUITO_BOM
    assert it["youtube_id"] == "abcdefghijk" and it["version_no"] == 2
    assert it["video_duration_s"] == 430  # duração conferida pelo avaliador

    # NONO — visitante (sem conta) abre vídeo, PDF e Falstad.
    data, _ = p.submissions.version_pdf(None, it["version_id"])
    assert b"%PDF" in data[:10]
    assert it["falstad_url"] == FALSTAD

    # Histórico de avaliações registra avaliador, versão e resultado.
    hist = p.reviews.history(monitor)
    assert [(h["decision"], h["version_no"], h["reviewer_name"]) for h in hist] == [
        (C.DECISION_APROVADA, 2, "Professora Responsável"),
        (C.DECISION_DEVOLVIDA, 1, "Monitor da Disciplina"),
    ]
    actions = [r["action"] for r in p.admin.logs(monitor)]
    for a in ("rascunho_criado", "submissao_enviada", "analise_iniciada", "devolvida", "reenvio", "aprovada", "publicada"):
        assert a in actions


def test_validacao_de_presenca_no_envio(platform, actors, exercise):
    p, ana = platform, actors["ana"]
    sid = p.submissions.start(ana, exercise.id)
    p.submissions.save_draft(ana, sid, expected_row_version=row_version(p, sid), youtube_url=YOUTUBE)
    import pytest
    from resolucoes.errors import ValidationError

    with pytest.raises(ValidationError) as exc:
        p.submissions.submit(ana, sid, expected_row_version=row_version(p, sid), declaration=True)
    assert "PDF" in exc.value.message and "Falstad" in exc.value.message
    assert p.submissions.detail(ana, sid)["submission"]["status"] == C.RASCUNHO


def test_aprovacao_exige_tres_materiais_e_criterios(platform, actors, exercise):
    import pytest
    from resolucoes.errors import ValidationError

    p, monitor = platform, actors["monitor"]
    sid = fill_and_submit(p, actors["ana"], exercise)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    with pytest.raises(ValidationError):
        p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level=C.EXCELENTE,
                          requirements={**ALL_REQ, "falstad": False}, criteria=GOOD_CRITERIA)
    bad = {**GOOD_CRITERIA, "calculos": {"rating": C.RATING_NAO_ATENDE, "comment": ""}}
    with pytest.raises(ValidationError):
        p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level=C.EXCELENTE,
                          requirements=ALL_REQ, criteria=bad)
    with pytest.raises(ValidationError):
        p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level="REGULAR",
                          requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    assert p.catalog.published() == []


def test_nova_versao_de_aprovada_nao_substitui_publicacao(platform, actors, exercise):
    p, monitor, ana = platform, actors["monitor"], actors["ana"]
    sid = fill_and_submit(p, ana, exercise)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level=C.BOM,
                      requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    v1_id = p.catalog.published()[0]["version_id"]

    p.submissions.new_version(ana, sid, expected_row_version=row_version(p, sid))
    p.submissions.save_draft(ana, sid, expected_row_version=row_version(p, sid),
                             youtube_url="https://youtube.com/shorts/ZZZZZZZZZZZ", falstad_url=FALSTAD,
                             duration_text="5:00", pdf_bytes=make_pdf("v2"), pdf_name="v2.pdf")
    # Rascunho não altera a publicação
    assert p.catalog.published()[0]["version_id"] == v1_id
    p.submissions.submit(ana, sid, expected_row_version=row_version(p, sid), declaration=True)
    assert p.catalog.published()[0]["version_id"] == v1_id
    assert p.submissions.detail(ana, sid)["submission"]["status"] == C.REENVIADA

    # Devolução da v2 mantém a v1 publicada
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    p.reviews.return_for_correction(monitor, sid, expected_row_version=row_version(p, sid), requirements=ALL_REQ,
                                    criteria=GOOD_CRITERIA, problems="O novo vídeo está sem áudio em 2:10.")
    pub = p.catalog.published()
    assert len(pub) == 1 and pub[0]["version_id"] == v1_id and pub[0]["level"] == C.BOM

    # v3 aprovada como Excelente substitui a publicação
    p.submissions.new_version(ana, sid, expected_row_version=row_version(p, sid))
    p.submissions.submit(ana, sid, expected_row_version=row_version(p, sid), declaration=True)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level=C.EXCELENTE,
                      requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    pub = p.catalog.published()
    assert pub[0]["version_no"] == 3 and pub[0]["level"] == C.EXCELENTE


def test_retirar_restaurar_e_ajustar_nivel(platform, actors, exercise):
    p, monitor, ana = platform, actors["monitor"], actors["ana"]
    sid = fill_and_submit(p, ana, exercise)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level=C.BOM,
                      requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    p.reviews.change_level(monitor, sid, expected_row_version=row_version(p, sid), level=C.MUITO_BOM,
                           justification="Revisão colegiada do nível.")
    assert p.catalog.published()[0]["level"] == C.MUITO_BOM
    p.reviews.retire(monitor, sid, expected_row_version=row_version(p, sid), reason="Vídeo removido pelo autor.")
    assert p.catalog.published() == []
    assert p.submissions.detail(ana, sid)["submission"]["status"] == C.RETIRADA
    v_id = p.submissions.detail(ana, sid)["published"]["id"]
    import pytest
    from resolucoes.errors import NotFound

    with pytest.raises(NotFound):  # PDF deixa de ser público após a retirada
        p.submissions.version_pdf(None, v_id)
    p.reviews.restore(monitor, sid, expected_row_version=row_version(p, sid))
    assert len(p.catalog.published()) == 1
    actions = [r["action"] for r in p.admin.logs(monitor)]
    assert {"nivel_alterado", "publicacao_retirada", "publicacao_restaurada"} <= set(actions)


def test_catalogo_agrupa_varias_resolucoes_do_mesmo_exercicio(platform, actors, exercise):
    p, monitor = platform, actors["monitor"]
    for student, level in ((actors["ana"], C.BOM), (actors["beto"], C.EXCELENTE)):
        sid = fill_and_submit(p, student, exercise)
        p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
        p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level=level,
                          requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    items = p.catalog.published()
    groups = group_by_exercise(items)
    assert len(groups) == 1 and len(groups[0]["resolutions"]) == 2
    assert groups[0]["featured"]["author_name"] == "Beto Lima"  # melhor nível em destaque
    assert len(filter_items(items, q="thevenin")) == 0
    assert len(filter_items(items, q="malhas")) == 2
    assert len(filter_items(items, q="2.04")) == 2
    assert len(filter_items(items, levels=[C.EXCELENTE])) == 1
    assert len(filter_items(items, units=["Unidade 2 — Métodos de Análise"])) == 2


def test_cancelar_envio_antes_da_analise_e_descartar_rascunho(platform, actors, exercise):
    p, ana, monitor = platform, actors["ana"], actors["monitor"]
    sid = fill_and_submit(p, ana, exercise)
    p.submissions.withdraw(ana, sid, expected_row_version=row_version(p, sid))
    det = p.submissions.detail(ana, sid)
    assert det["submission"]["status"] == C.RASCUNHO and det["current"]["state"] == C.V_RASCUNHO
    p.submissions.submit(ana, sid, expected_row_version=row_version(p, sid), declaration=True)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    import pytest
    from resolucoes.errors import ConflictError

    with pytest.raises(ConflictError):  # em análise: bloqueado
        p.submissions.withdraw(ana, sid, expected_row_version=row_version(p, sid))
    with pytest.raises(ConflictError):
        p.submissions.save_draft(ana, sid, expected_row_version=row_version(p, sid), youtube_url=YOUTUBE)

    # Rascunho nunca enviado pode ser excluído por completo
    other = p.exercises.create(monitor, code="3.01", title="Thévenin", statement="Encontre Vth.", unit="Unidade 3")
    sid2 = p.submissions.start(ana, other.id)
    p.submissions.save_draft(ana, sid2, expected_row_version=row_version(p, sid2), pdf_bytes=make_pdf(), pdf_name="a.pdf")
    assert p.submissions.discard_draft(ana, sid2, expected_row_version=row_version(p, sid2)) is True
    with p.engine.connect() as conn:
        assert conn.execute(sa.select(sa.func.count()).select_from(db.submissions).where(db.submissions.c.id == sid2)).scalar_one() == 0


def test_codigo_do_exercicio_protegido_apos_entregas(platform, actors, exercise):
    import pytest
    from resolucoes.errors import ConflictError

    p, monitor = platform, actors["monitor"]
    p.submissions.start(actors["ana"], exercise.id)
    with pytest.raises(ConflictError):
        p.exercises.update(monitor, exercise.id, code="2.05", title=exercise.title, statement=exercise.statement,
                           unit=exercise.unit)
    # título pode mudar
    ex = p.exercises.update(monitor, exercise.id, code="2.04", title="Análise de Malhas (revisado)",
                            statement=exercise.statement, unit=exercise.unit)
    assert ex.title.endswith("(revisado)")
    with pytest.raises(ConflictError):
        p.exercises.delete(monitor, exercise.id)
    p.exercises.set_active(monitor, exercise.id, False)
    assert p.exercises.list(actors["beto"]) == []


def test_desativar_aluno_preserva_publicacoes(platform, actors, exercise):
    p, monitor, ana = platform, actors["monitor"], actors["ana"]
    sid = fill_and_submit(p, ana, exercise)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level=C.BOM,
                      requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    p.users.set_active(monitor, ana.id, False)
    assert len(p.catalog.published()) == 1
    assert p.reviews.history(monitor)[0]["author_name"] == "Ana Souza"
