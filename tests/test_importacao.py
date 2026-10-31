"""Importação das Listas 03 e 04 (Boylestad, cap. 8) com figuras."""

from __future__ import annotations

import dataclasses
import re

import pytest
import sqlalchemy as sa

from resolucoes import constants as C
from resolucoes import db, importacao
from resolucoes.services import Platform
from resolucoes.services.exercises import CONTENT_ROOT, list_label

from conftest import ALL_REQ, FALSTAD, GOOD_CRITERIA, FakeYouTube, make_pdf, row_version

SPEC = importacao.PACKS[0]
PACK_DIR = CONTENT_ROOT / SPEC["id"]
RAW = (PACK_DIR / SPEC["fichas"]).read_text(encoding="utf-8-sig")


@pytest.fixture(scope="module")
def pack():
    return importacao.load_pack(SPEC)


@pytest.fixture
def seeded(platform):
    """Plataforma iniciada como em produção (importação automática ligada)."""
    s = dataclasses.replace(platform.settings, seed_content=True)
    return Platform(s, engine=platform.engine, store=platform.store, http_get=FakeYouTube())


# --------------------------------------------------------------------------- #
# Integridade do conteúdo do pacote
# --------------------------------------------------------------------------- #
def test_pacote_integro(pack):
    assert pack.problems == []
    assert len(pack.fichas) == 49
    l3 = [f for f in pack.fichas if f.lista == "03"]
    l4 = [f for f in pack.fichas if f.lista == "04"]
    assert len(l3) == 27 and len(l4) == 22
    assert [f.code for f in l3] == [f"3.{i:02d}" for i in range(1, 28)]
    assert [f.code for f in l4] == [f"4.{i:02d}" for i in range(1, 23)]
    assert len({f.code for f in pack.fichas}) == 49
    assert all(f.available for f in pack.fichas)


def test_campos_preservados_do_arquivo_do_docente(pack):
    for f in pack.fichas:
        for value in (f.title, f.unit, f.topics, f.statement, f.description):
            assert value and value in RAW, (f.code, value[:60])
        # Materiais de apoio: referência bibliográfica intacta.
        ref_line = f.support_material.splitlines()[0]
        assert ref_line in RAW
        assert "BOYLESTAD" in ref_line and "12. ed." in ref_line and "Capítulo 8" in ref_line
        assert f"Problema {f.problema}," in ref_line and f.figure_label in ref_line and "p. " in ref_line
        assert f"problema {f.problema}" in f.title
        # A instrução ao docente ("publicar ou anexar") foi cumprida e substituída.
        assert "publicar ou anexar" not in f.support_material
        assert f.figure_file in f.support_material


def test_figuras_existem_e_correspondem_ao_indice(pack):
    pngs = {p.name for p in (PACK_DIR / "Figuras").glob("*.png")}
    assert len(pngs) == 38
    assert {f.figure_file for f in pack.fichas} == pngs  # todas usadas, nenhuma sobrando
    for f in pack.fichas:
        assert pack.indice[(f.lista, f.problema)] == f.figure_file
        assert f.figure_label.replace("Figura ", "FIG_").replace(".", "_") + ".png" == f.figure_file
        assert f.figure_label in f.statement or f.figure_label in f.description


def test_figuras_compartilhadas(pack):
    by_fig: dict[str, list[str]] = {}
    for f in pack.fichas:
        by_fig.setdefault(f.figure_file, []).append(f.code)
    assert by_fig["FIG_8_135.png"] == ["4.17", "4.18"]
    assert by_fig["FIG_8_136.png"] == ["4.19", "4.20"]
    assert sorted(by_fig["FIG_8_113.png"]) == ["3.07", "3.14", "4.01"]


def test_problemas_57_a_60_somente_itens_a_b(pack):
    alvo = [f for f in pack.fichas if f.lista == "04" and f.problema in (57, 58, 59, 60)]
    assert [f.code for f in alvo] == ["4.17", "4.18", "4.19", "4.20"]
    for f in alvo:
        assert re.findall(r"^([a-z])\)", f.statement, re.M) == ["a", "b"]
        assert "somente os itens a e b" in f.statement


def test_sem_solucoes_publicadas(pack):
    for f in pack.fichas:
        text = f"{f.statement}\n{f.description}\n{f.support_material}".lower()
        for word in ("resposta:", "solução:", "gabarito", "resultado esperado"):
            assert word not in text, (f.code, word)


# --------------------------------------------------------------------------- #
# Importação no banco real
# --------------------------------------------------------------------------- #
def test_importacao_cadastra_49_com_figuras(seeded, actors):
    p, ana = seeded, actors["ana"]
    exs = p.exercises.list(ana)
    assert len(exs) == 64
    assert sum(1 for e in exs if list_label(e.code) == "Adicional") == 15
    assert sum(1 for e in exs if list_label(e.code) == "Lista 03") == 27
    assert sum(1 for e in exs if list_label(e.code) == "Lista 04") == 22
    expected = {f.code: f for f in importacao.load_pack(SPEC).fichas}
    refs = set()
    for ex in exs:
        if ex.code not in expected:
            continue
        f = expected[ex.code]
        assert (ex.title, ex.unit, ex.statement, ex.description) == (f.title, f.unit, f.statement, f.description)
        figs = p.exercises.figures(ex.id)
        assert len(figs) == 1
        fig = figs[0]
        assert fig.ref.endswith("/" + f.figure_file) and fig.label == f.figure_label and fig.source == "pacote"
        assert fig.width and fig.height
        data = p.exercises.figure_bytes(fig)
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        refs.add(fig.ref)
    assert len(refs) == 38


def test_importacao_idempotente_e_persistente(seeded, actors):
    p = seeded
    importacao.ensure_packs(p)  # repetir
    p2 = Platform(p.settings, engine=p.engine, store=p.store, http_get=FakeYouTube())  # "reinício"
    with p2.engine.connect() as conn:
        n_ex = conn.execute(sa.select(sa.func.count()).select_from(db.exercises)).scalar_one()
        n_fig = conn.execute(sa.select(sa.func.count()).select_from(db.exercise_figures)).scalar_one()
        n_log = conn.execute(sa.select(sa.func.count()).select_from(db.audit_log)
                             .where(db.audit_log.c.action == "pacote_importado")).scalar_one()
    assert (n_ex, n_fig, n_log) == (64, 64, 2)
    assert importacao.pack_status(p2, SPEC["id"])["criados"].__len__() == 49


def test_nao_sobrescreve_exercicio_do_professor(platform, actors):
    p, monitor = platform, actors["monitor"]
    own = p.exercises.create(monitor, code="3.01", title="Exercício do professor", statement="Texto próprio.",
                             unit="Unidade 3")
    seeded = Platform(dataclasses.replace(p.settings, seed_content=True), engine=p.engine, store=p.store,
                      http_get=FakeYouTube())
    kept = seeded.exercises.get(own.id)
    assert (kept.title, kept.statement) == ("Exercício do professor", "Texto próprio.")
    assert seeded.exercises.figures(own.id) == []
    status = importacao.pack_status(seeded, SPEC["id"])
    assert status["mantidos_sem_alteracao"] == ["3.01"] and len(status["criados"]) == 48


def test_excluido_nao_volta_sozinho_mas_pode_ser_reimportado(seeded, actors):
    p, monitor = seeded, actors["monitor"]
    ex = next(e for e in p.exercises.list(monitor, include_inactive=True) if e.code == "4.22")
    p.exercises.delete(monitor, ex.id)
    Platform(p.settings, engine=p.engine, store=p.store, http_get=FakeYouTube())  # reinício
    assert "4.22" not in {e.code for e in p.exercises.list(monitor, include_inactive=True)}
    with pytest.raises(Exception):
        importacao.reimport(p, actors["ana"], SPEC["id"])  # aluno não pode
    rep = importacao.reimport(p, monitor, SPEC["id"])
    assert rep["criados"] == ["4.22"] and len(rep["mantidos_sem_alteracao"]) == 48


def test_entrega_completa_em_exercicio_importado(seeded, actors):
    """O fluxo de entrega (YouTube + PDF + Falstad) não muda para os exercícios importados."""
    p, ana, monitor = seeded, actors["ana"], actors["monitor"]
    ex = next(e for e in p.exercises.list(ana) if e.code == "4.17")
    sid = p.submissions.start(ana, ex.id)
    p.submissions.save_draft(ana, sid, expected_row_version=row_version(p, sid),
                             youtube_url="https://youtu.be/dQw4w9WgXcQ", falstad_url=FALSTAD, duration_text="5:00",
                             pdf_bytes=make_pdf("4.17"), pdf_name="r.pdf")
    from resolucoes.errors import ValidationError

    with pytest.raises(ValidationError):  # declaração continua obrigatória
        p.submissions.submit(ana, sid, expected_row_version=row_version(p, sid), declaration=False)
    p.submissions.submit(ana, sid, expected_row_version=row_version(p, sid), declaration=True)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level=C.BOM,
                      requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    item = p.catalog.get(sid)
    assert item["code"] == "4.17" and "Figura 8.135" in item["statement"]


def test_figura_enviada_pela_administracao(seeded, actors):
    from PIL import Image
    import io

    p, monitor = seeded, actors["monitor"]
    ex = p.exercises.create(monitor, code="5.01", title="Novo", statement="Veja a figura.", unit="Unidade 5")
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), "white").save(buf, format="PNG")
    fig = p.exercises.add_figure(monitor, ex.id, buf.getvalue(), label="Figura X", caption="Fonte própria")
    assert fig.source == "arquivo" and p.exercises.figure_bytes(fig)[:4] == b"\x89PNG"
    from resolucoes.errors import PermissionDenied, ValidationError

    with pytest.raises(PermissionDenied):
        p.exercises.add_figure(actors["ana"], ex.id, buf.getvalue())
    with pytest.raises(ValidationError):
        p.exercises.add_figure(monitor, ex.id, b"%PDF-1.4 nao e imagem")
    p.exercises.remove_figure(monitor, fig.id)
    assert p.exercises.figures(ex.id) == [] and not p.store.exists(fig.ref)
