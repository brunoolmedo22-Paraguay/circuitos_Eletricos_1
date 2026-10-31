import dataclasses
import sqlalchemy as sa
from resolucoes import db
from resolucoes.services import Platform
"""Testes do pacote adicional de 15 exercícios."""
from resolucoes import importacao
from resolucoes.services.exercises import list_label
from resolucoes.validators import normalize_exercise_code


def test_pacote_adicional():
    spec = next(x for x in importacao.PACKS if x.get("marcador") == "boylestad_12ed_cap8_adicional")
    pack = importacao.load_pack(spec)
    assert pack.problems == []
    assert len(pack.fichas) == 15
    assert [f.code for f in pack.fichas] == [f"A.{i:02d}" for i in range(1, 16)]
    assert all(f.figure_file for f in pack.fichas)
    assert all(f.available for f in pack.fichas)
    assert len({f.figure_file for f in pack.fichas}) == 15
    assert len({f.problema for f in pack.fichas}) == 15


def test_codigos_adicionais():
    assert normalize_exercise_code("A.01") == "a.01"
    assert list_label("a.01") == "Adicional"


def test_importacao_64_exercicios_64_figuras(platform):
    settings = dataclasses.replace(platform.settings, seed_content=True)
    app = Platform(settings, engine=platform.engine, store=platform.store)
    with app.engine.connect() as conn:
        assert conn.execute(sa.select(sa.func.count()).select_from(db.exercises)).scalar_one() == 64
        assert conn.execute(sa.select(sa.func.count()).select_from(db.exercise_figures)).scalar_one() == 64
        assert conn.execute(sa.select(sa.func.count()).select_from(db.exercises).where(db.exercises.c.active.is_(True))).scalar_one() == 64
    Platform(settings, engine=platform.engine, store=platform.store)
    with app.engine.connect() as conn:
        assert conn.execute(sa.select(sa.func.count()).select_from(db.exercises)).scalar_one() == 64
        assert conn.execute(sa.select(sa.func.count()).select_from(db.exercise_figures)).scalar_one() == 64


def test_svg_renderizado_pelo_streamlit():
    from pathlib import Path
    from streamlit.elements.lib.image_utils import image_to_url
    import streamlit as st
    root = Path(__file__).resolve().parents[1] / "conteudo/pacotes/boylestad_12ed_cap8_listas_03_04/Figuras"
    data = (root / "FIG_8_97.svg").read_bytes()
    assert data.startswith(b"<svg")
    markup = data.decode("utf-8-sig")
    assert markup.startswith("<svg")
    url = image_to_url(markup, 500, False, "RGB", "PNG", "test-svg")
    assert url.startswith("data:image/svg+xml")
