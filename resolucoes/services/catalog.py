"""Catálogo público de Exercícios Resolvidos (somente publicações aprovadas)."""

from __future__ import annotations

import unicodedata

import sqlalchemy as sa

from .. import constants as C
from .. import db

SORT_OPTIONS = {
    "recentes": "Publicados recentemente",
    "codigo": "Número do exercício",
    "nivel": "Nível de aprovação",
    "titulo": "Título (A–Z)",
}


def fold(text: str) -> str:
    """Minúsculas sem acentos, para busca tolerante (Thévenin = thevenin)."""
    norm = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in norm if not unicodedata.combining(ch)).lower()


class CatalogService:
    def __init__(self, platform):
        self.p = platform

    def _query(self):
        return (
            sa.select(
                db.submissions.c.id.label("submission_id"),
                db.submissions.c.coauthors,
                db.submissions.c.published_level.label("level"),
                db.submissions.c.published_at,
                db.submissions.c.first_approved_at,
                db.submissions.c.resource_alert,
                db.exercises.c.id.label("exercise_id"),
                db.exercises.c.code,
                db.exercises.c.title,
                db.exercises.c.unit,
                db.exercises.c.topics,
                db.exercises.c.statement,
                db.exercises.c.description,
                db.exercises.c.support_material,
                db.exercises.c.sort_key,
                sa.func.coalesce(db.users.c.public_name, db.users.c.full_name).label("author_name"),
                db.versions.c.id.label("version_id"),
                db.versions.c.version_no,
                db.versions.c.youtube_id,
                db.versions.c.youtube_url,
                db.versions.c.youtube_title,
                db.versions.c.video_duration_s,
                db.versions.c.video_duration_source,
                db.versions.c.falstad_url,
                db.versions.c.pdf_pages,
                db.versions.c.pdf_size,
            )
            .join(db.exercises, db.exercises.c.id == db.submissions.c.exercise_id)
            .join(db.users, db.users.c.id == db.submissions.c.author_id)
            .join(db.versions, db.versions.c.id == db.submissions.c.published_version_id)
            .where(db.submissions.c.is_published.is_(True))
        )

    @staticmethod
    def _shape(row) -> dict:
        d = dict(row._mapping)
        # Só exibimos duração obtida de forma confiável (API do YouTube ou conferida pelo avaliador).
        if d["video_duration_source"] not in ("api", "verificada"):
            d["video_duration_s"] = None
        d["topic_list"] = [t.strip() for t in (d["topics"] or "").split(",") if t.strip()]
        return d

    def published(self) -> list[dict]:
        with self.p.engine.connect() as conn:
            return [self._shape(r) for r in conn.execute(self._query())]

    def get(self, submission_id: str) -> dict | None:
        with self.p.engine.connect() as conn:
            row = conn.execute(self._query().where(db.submissions.c.id == submission_id)).first()
        return self._shape(row) if row else None

    def for_exercise(self, exercise_id: str) -> list[dict]:
        with self.p.engine.connect() as conn:
            rows = [self._shape(r) for r in conn.execute(self._query().where(db.exercises.c.id == exercise_id))]
        return sorted(rows, key=lambda r: (C.LEVEL_ORDER.get(r["level"], 9), r["first_approved_at"] or r["published_at"]))


def filter_items(items: list[dict], *, q: str = "", units: list[str] | None = None,
                 levels: list[str] | None = None) -> list[dict]:
    out = items
    if units:
        out = [i for i in out if i["unit"] in units]
    if levels:
        out = [i for i in out if i["level"] in levels]
    if q and q.strip():
        terms = fold(q).split()

        def hay(i):
            return fold(" ".join([
                i["code"], f"exercicio {i['code']}", i["title"], i["unit"], i["topics"], i["statement"],
                i["description"], i["author_name"], i["coauthors"] or "", i.get("youtube_title") or "",
            ]))

        out = [i for i in out if all(t in hay(i) for t in terms)]
    return out


def group_by_exercise(items: list[dict], *, sort: str = "recentes") -> list[dict]:
    """Uma entrada por exercício, com a resolução em destaque e as demais agrupadas.

    Destaque: melhor nível; em empate, a aprovação mais antiga (quem publicou primeiro).
    """
    groups: dict[str, dict] = {}
    for it in items:
        g = groups.setdefault(it["exercise_id"], {"exercise_id": it["exercise_id"], "code": it["code"],
                                                  "title": it["title"], "unit": it["unit"],
                                                  "sort_key": it["sort_key"], "resolutions": []})
        g["resolutions"].append(it)
    for g in groups.values():
        g["resolutions"].sort(key=lambda r: (C.LEVEL_ORDER.get(r["level"], 9), r["first_approved_at"] or r["published_at"]))
        g["featured"] = g["resolutions"][0]
        g["latest"] = max(r["published_at"] for r in g["resolutions"])
        g["best_level"] = g["featured"]["level"]
    result = list(groups.values())
    if sort == "codigo":
        result.sort(key=lambda g: g["sort_key"])
    elif sort == "nivel":
        result.sort(key=lambda g: (C.LEVEL_ORDER.get(g["best_level"], 9), g["sort_key"]))
    elif sort == "titulo":
        result.sort(key=lambda g: fold(g["title"]))
    else:
        result.sort(key=lambda g: g["latest"], reverse=True)
    return result
