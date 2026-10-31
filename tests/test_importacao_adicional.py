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
    assert len({f.problema for f in pack.fichas}) == 15


def test_codigos_adicionais():
    assert normalize_exercise_code("A.01") == "a.01"
    assert list_label("a.01") == "Adicional"
