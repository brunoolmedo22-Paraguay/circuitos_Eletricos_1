"""Catálogo de Exercícios Propostos (gerenciado pela administração)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

import sqlalchemy as sa

from .. import constants as C
from .. import db
from ..errors import ConflictError, NotFound, ValidationError
from ..validators import exercise_sort_key, normalize_exercise_code
from .common import User, audit, clean_text, require_admin, require_user


@dataclass(frozen=True)
class Exercise:
    id: str
    code: str
    title: str
    statement: str
    unit: str
    topics: str
    description: str
    support_material: str
    active: bool
    created_at: datetime
    updated_at: datetime
    submissions_count: int = 0

    @property
    def label(self) -> str:
        return f"Exercício {self.code} — {self.title}"

    @property
    def topic_list(self) -> list[str]:
        return [t.strip() for t in self.topics.split(",") if t.strip()]


def _row(row, count: int = 0) -> Exercise:
    m = row._mapping
    return Exercise(
        id=m["id"], code=m["code"], title=m["title"], statement=m["statement"], unit=m["unit"] or "",
        topics=m["topics"] or "", description=m["description"] or "", support_material=m["support_material"] or "",
        active=bool(m["active"]), created_at=m["created_at"], updated_at=m["updated_at"], submissions_count=count,
    )


class ExerciseService:
    def __init__(self, platform):
        self.p = platform

    def _counts(self, conn) -> dict[str, int]:
        rows = conn.execute(
            sa.select(db.submissions.c.exercise_id, sa.func.count()).group_by(db.submissions.c.exercise_id)
        )
        return {r[0]: r[1] for r in rows}

    def list(self, actor: User | None, *, include_inactive: bool = False) -> list[Exercise]:
        """Alunos veem somente exercícios ativos; administradores podem ver todos."""
        require_user(actor)
        if include_inactive:
            require_admin(actor)
        stmt = sa.select(db.exercises).order_by(db.exercises.c.sort_key)
        if not include_inactive:
            stmt = stmt.where(db.exercises.c.active.is_(True))
        with self.p.engine.connect() as conn:
            counts = self._counts(conn) if include_inactive else {}
            return [_row(r, counts.get(r._mapping["id"], 0)) for r in conn.execute(stmt)]

    def get(self, exercise_id: str, *, conn=None) -> Exercise:
        def _do(c):
            row = c.execute(sa.select(db.exercises).where(db.exercises.c.id == exercise_id)).first()
            if row is None:
                raise NotFound("Exercício não encontrado.")
            return _row(row)

        if conn is not None:
            return _do(conn)
        with self.p.engine.connect() as c:
            return _do(c)

    def _clean(self, *, title, statement, unit, topics, description, support_material) -> dict:
        return dict(
            title=clean_text(title, max_len=200, field="titulo", label="Título", required=True),
            statement=clean_text(statement, max_len=20000, field="enunciado", label="Enunciado", required=True),
            unit=clean_text(unit, max_len=160, field="unidade", label="Unidade ou tema", required=True),
            topics=", ".join(t.strip() for t in clean_text(topics, max_len=500, field="temas", label="Temas e conceitos").split(",") if t.strip()),
            description=clean_text(description, max_len=5000, field="descricao", label="Descrição complementar"),
            support_material=clean_text(support_material, max_len=5000, field="material", label="Materiais de apoio"),
        )

    def create(self, actor: User, *, code, title, statement, unit, topics="", description="",
               support_material="", active=True) -> Exercise:
        require_admin(actor)
        code_n = normalize_exercise_code(code)
        data = self._clean(title=title, statement=statement, unit=unit, topics=topics,
                           description=description, support_material=support_material)
        now = db.utcnow()
        eid = str(uuid.uuid4())
        with self.p.engine.begin() as conn:
            if conn.execute(sa.select(db.exercises.c.id).where(db.exercises.c.code == code_n)).first():
                raise ValidationError(f"Já existe um exercício com o código {code_n}.", field="codigo")
            conn.execute(
                db.exercises.insert().values(
                    id=eid, code=code_n, active=bool(active), sort_key=exercise_sort_key(code_n),
                    created_at=now, updated_at=now, created_by=actor.id, updated_by=actor.id, **data,
                )
            )
            audit(conn, C.LOG_EXERCICIO, "exercicio_criado", actor, target_type="exercicio", target_id=eid,
                  summary=f"Exercício {code_n} criado: {data['title']}")
            return self.get(eid, conn=conn)

    def update(self, actor: User, exercise_id: str, *, code, title, statement, unit, topics="",
               description="", support_material="") -> Exercise:
        require_admin(actor)
        code_n = normalize_exercise_code(code)
        data = self._clean(title=title, statement=statement, unit=unit, topics=topics,
                           description=description, support_material=support_material)
        with self.p.engine.begin() as conn:
            cur = self.get(exercise_id, conn=conn)
            if code_n != cur.code:
                linked = conn.execute(
                    sa.select(sa.func.count()).select_from(db.submissions).where(db.submissions.c.exercise_id == exercise_id)
                ).scalar_one()
                if linked:
                    raise ConflictError(
                        f"O código {cur.code} não pode ser alterado: já existem {linked} submissão(ões) vinculada(s)."
                    )
                if conn.execute(sa.select(db.exercises.c.id).where(db.exercises.c.code == code_n)).first():
                    raise ValidationError(f"Já existe um exercício com o código {code_n}.", field="codigo")
            changed = [k for k, v in data.items() if getattr(cur, k) != v] + (["code"] if code_n != cur.code else [])
            conn.execute(
                db.exercises.update().where(db.exercises.c.id == exercise_id).values(
                    code=code_n, sort_key=exercise_sort_key(code_n), updated_at=db.utcnow(), updated_by=actor.id, **data
                )
            )
            if changed:
                audit(conn, C.LOG_EXERCICIO, "exercicio_editado", actor, target_type="exercicio", target_id=exercise_id,
                      summary=f"Exercício {code_n} editado", campos=changed)
            return self.get(exercise_id, conn=conn)

    def set_active(self, actor: User, exercise_id: str, active: bool) -> Exercise:
        require_admin(actor)
        with self.p.engine.begin() as conn:
            cur = self.get(exercise_id, conn=conn)
            conn.execute(
                db.exercises.update().where(db.exercises.c.id == exercise_id).values(
                    active=bool(active), updated_at=db.utcnow(), updated_by=actor.id
                )
            )
            audit(conn, C.LOG_EXERCICIO, "exercicio_ativado" if active else "exercicio_desativado", actor,
                  target_type="exercicio", target_id=exercise_id,
                  summary=f"Exercício {cur.code} {'disponibilizado' if active else 'indisponibilizado'} para novas entregas")
            return self.get(exercise_id, conn=conn)

    def delete(self, actor: User, exercise_id: str) -> None:
        require_admin(actor)
        with self.p.engine.begin() as conn:
            cur = self.get(exercise_id, conn=conn)
            linked = conn.execute(
                sa.select(sa.func.count()).select_from(db.submissions).where(db.submissions.c.exercise_id == exercise_id)
            ).scalar_one()
            if linked:
                raise ConflictError("Este exercício possui submissões e não pode ser excluído. Desative-o em vez disso.")
            conn.execute(db.exercises.delete().where(db.exercises.c.id == exercise_id))
            audit(conn, C.LOG_EXERCICIO, "exercicio_excluido", actor, target_type="exercicio", target_id=exercise_id,
                  summary=f"Exercício {cur.code} excluído (sem submissões)")
