"""Repositório de consulta teórica baseado exclusivamente no livro de Boylestad."""

from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

from .formulas import get_formula

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "teoria.json"
FORMULAS_FILE = ROOT / "data" / "formulas.json"

FREQUENT_IDS = [
    "lei_ohm_teoria",
    "tensao",
    "corrente",
    "resistencia",
    "potencia",
    "energia_eletrica_teoria",
    "eficiencia_teoria",
    "circuito_serie",
    "circuito_paralelo",
    "kvl_teoria",
    "kcl_teoria",
    "divisor_tensao_teoria",
    "divisor_corrente_teoria",
    "analise_malhas",
    "analise_nodal",
    "thevenin_teoria",
    "norton_teoria",
    "superposicao_teoria",
    "capacitor",
    "transitorio_rc",
    "indutor",
    "transitorio_rl",
    "senoide",
    "impedancia",
]


def _norm(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(ch for ch in text if not unicodedata.combining(ch)).casefold().strip()


@lru_cache(maxsize=1)
def _load() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _formula_data() -> dict:
    return json.loads(FORMULAS_FILE.read_text(encoding="utf-8"))


def metadata() -> dict:
    data = _load()
    return {
        **data.get("metadata", {}),
        "theory_count": len(data.get("theories", [])),
        "chapter_count": len(_formula_data().get("chapters", [])),
    }


def all_theories() -> list[dict]:
    return list(_load().get("theories", []))


def frequent_theories(limit: int = 24) -> list[dict]:
    by_id = {row["id"]: row for row in all_theories()}
    ordered = [by_id[item_id] for item_id in FREQUENT_IDS if item_id in by_id]
    return ordered[:limit]


def chapters() -> list[dict]:
    return list(_formula_data().get("chapters", []))


def topics() -> list[str]:
    values = {topic for row in all_theories() for topic in row.get("topics", [])}
    return sorted(values, key=_norm)


def by_chapter(number: int) -> list[dict]:
    return [row for row in all_theories() if int(row.get("chapter", -1)) == int(number)]


def by_topic(topic: str) -> list[dict]:
    target = _norm(topic)
    return [
        row for row in all_theories()
        if any(_norm(item) == target for item in row.get("topics", []))
    ]


def search_theories(query: str, limit: int = 60) -> list[dict]:
    q = _norm(query)
    if not q:
        return frequent_theories(limit=min(limit, 24))

    scored: list[tuple[int, dict]] = []
    for row in all_theories():
        title = _norm(row.get("title", ""))
        topics_text = " ".join(_norm(x) for x in row.get("topics", []))
        aliases_text = " ".join(_norm(x) for x in row.get("aliases", []))
        summary = _norm(row.get("summary", ""))
        chapter_title = _norm(next(
            (c.get("title", "") for c in chapters() if c.get("number") == row.get("chapter")),
            "",
        ))

        score = 0
        if q == title:
            score += 120
        elif q in title:
            score += 80
        if q in aliases_text:
            score += 55
        if q in topics_text:
            score += 45
        if q in chapter_title:
            score += 30
        if q in summary:
            score += 16

        # Busca por várias palavras: todas presentes no texto também contam.
        tokens = [token for token in q.split() if len(token) > 1]
        haystack = " ".join([title, topics_text, aliases_text, summary, chapter_title])
        if tokens and all(token in haystack for token in tokens):
            score += 20

        if score:
            scored.append((score, row))

    scored.sort(key=lambda item: (-item[0], item[1].get("chapter", 0), item[1].get("title", "")))
    return [row for _, row in scored[:limit]]


def formulas_for(theory: dict, limit: int = 3) -> list[dict]:
    rows: list[dict] = []
    for formula_id in theory.get("formula_ids", []):
        formula = get_formula(formula_id)
        if formula:
            rows.append(formula)
        if len(rows) >= limit:
            break
    return rows
