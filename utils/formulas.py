"""Catálogo, filtros y búsqueda del formulario de Circuitos Eléctricos I."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT_DIR / "data" / "formulas.json"

# Orden deliberado para que la portada empiece por las relaciones que más se
# consultan durante resolución de circuitos, no por el orden del libro.
FREQUENT_IDS = [
    "ohms_law",
    "power_vi",
    "joule_loss",
    "kvl",
    "kcl",
    "voltage_divider",
    "current_divider",
    "series_resistance",
    "parallel_resistance",
    "parallel_two_resistors",
    "thevenin_voltage",
    "thevenin_resistance",
    "norton_current",
    "max_power_dc",
    "rc_tau",
    "capacitor_energy",
    "inductor_energy",
    "sine_rms",
    "inductive_reactance",
    "capacitive_reactance",
    "ac_ohm",
    "real_power",
    "reactive_power",
    "apparent_power",
]


_TOKEN_EQUIV = {
    "corrente": "corriente",
    "correntes": "corriente",
    "tensao": "tension",
    "tensoes": "tension",
    "voltaje": "tension",
    "voltagem": "tension",
    "resistor": "resistencia",
    "resistores": "resistencia",
    "resistencias": "resistencia",
    "perda": "perdida",
    "perdas": "perdida",
    "perdidas": "perdida",
    "potencias": "potencia",
    "capacitor": "capacitancia",
    "capacitores": "capacitancia",
    "indutor": "inductancia",
    "indutores": "inductancia",
    "inductor": "inductancia",
    "inductores": "inductancia",
    "frequencia": "frecuencia",
    "frecuencias": "frecuencia",
    "tevenin": "thevenin",
}


def _norm(value: object) -> str:
    text = str(value or "").lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [_TOKEN_EQUIV.get(token, token) for token in text.split()]
    return " ".join(tokens)


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    with CATALOG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def formulas() -> list[dict]:
    return list(load_catalog()["formulas"])


def metadata() -> dict:
    return dict(load_catalog()["metadata"])


def chapters() -> list[dict]:
    return list(load_catalog()["chapters"])


def topics() -> list[str]:
    values = {topic for formula in formulas() for topic in formula.get("topics", [])}
    return sorted(values, key=_norm)


def get_formula(formula_id: str | None) -> dict | None:
    if not formula_id:
        return None
    return next((f for f in formulas() if f["id"] == formula_id), None)


def frequent_formulas(limit: int | None = None) -> list[dict]:
    by_id = {f["id"]: f for f in formulas()}
    ordered = [by_id[fid] for fid in FREQUENT_IDS if fid in by_id]
    if limit is not None:
        return ordered[:limit]
    return ordered


def by_chapter(chapter_number: int) -> list[dict]:
    return [f for f in formulas() if int(f["chapter"]) == int(chapter_number)]


def by_topic(topic: str) -> list[dict]:
    needle = _norm(topic)
    return [
        f
        for f in formulas()
        if any(_norm(item) == needle for item in f.get("topics", []))
    ]


def _search_blob(formula: dict) -> str:
    parts: list[str] = [
        formula.get("name", ""),
        formula.get("latex", ""),
        formula.get("chapter_title", ""),
        formula.get("section", ""),
        formula.get("note", ""),
        " ".join(formula.get("topics", [])),
        " ".join(formula.get("aliases", [])),
        " ".join(formula.get("variants", [])),
        " ".join(formula.get("variables", {}).keys()),
        " ".join(formula.get("variables", {}).values()),
    ]
    return _norm(" ".join(parts))


def search_formulas(query: str, limit: int = 60) -> list[dict]:
    """Búsqueda tolerante por nombre, tema, alias, variable y referencia.

    Da más peso a coincidencias en el nombre y en los aliases, y exige que todos
    los términos de una consulta multi-palabra estén presentes en el registro.
    """
    q = _norm(query)
    if not q:
        return frequent_formulas(limit=24)

    tokens = [t for t in q.split() if t]
    ranked: list[tuple[int, int, dict]] = []

    for idx, formula in enumerate(formulas()):
        blob = _search_blob(formula)
        matched_tokens = sum(1 for token in tokens if token in blob)
        required_tokens = len(tokens) if len(tokens) <= 2 else len(tokens) - 1
        if matched_tokens < required_tokens:
            continue

        name = _norm(formula.get("name"))
        aliases = _norm(" ".join(formula.get("aliases", [])))
        topics_blob = _norm(" ".join(formula.get("topics", [])))

        score = 0
        if q == name:
            score += 100
        if q in name:
            score += 45
        if q in aliases:
            score += 36
        if q in topics_blob:
            score += 28
        score += matched_tokens * 8
        score += sum(12 for token in tokens if token in name)
        score += sum(9 for token in tokens if token in aliases)
        score += sum(6 for token in tokens if token in topics_blob)
        if formula.get("frequent"):
            score += 2

        ranked.append((score, -idx, formula))

    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [row[2] for row in ranked[:limit]]


def related_formulas(formula: dict, limit: int = 5) -> list[dict]:
    source_topics = {_norm(t) for t in formula.get("topics", [])}
    scored: list[tuple[int, dict]] = []
    for candidate in formulas():
        if candidate["id"] == formula["id"]:
            continue
        overlap = len(source_topics & {_norm(t) for t in candidate.get("topics", [])})
        if overlap:
            scored.append((overlap, candidate))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["chapter"], pair[1]["name"]))
    return [formula for _, formula in scored[:limit]]
