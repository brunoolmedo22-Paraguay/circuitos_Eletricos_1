"""Catálogo de Exercícios Propostos (gerenciado pela administração)."""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa

from .. import constants as C
from .. import db
from ..errors import ConflictError, NotFound, StorageFailure, ValidationError
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


# Raiz dos pacotes de conteúdo versionados com o código (figuras do livro etc.).
CONTENT_ROOT = Path(__file__).resolve().parent.parent.parent / "conteudo" / "pacotes"
FIG_PACOTE = "pacote"
FIG_ARQUIVO = "arquivo"
MAX_FIGURE_MB = 5


@dataclass(frozen=True)
class Figure:
    id: str
    exercise_id: str
    position: int
    source: str
    ref: str
    label: str
    caption: str
    width: int | None
    height: int | None


def _fig(row) -> Figure:
    m = row._mapping
    return Figure(id=m["id"], exercise_id=m["exercise_id"], position=m["position"], source=m["source"], ref=m["ref"],
                  label=m["label"] or "", caption=m["caption"] or "", width=m["width"], height=m["height"])


def list_label(code: str) -> str:
    """Rótulo da lista a partir do código (3.01 → "Lista 03")."""
    head = (code or "").split(".")[0]
    return f"Lista {int(head):02d}" if head.isdigit() else "Outros"


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
        with self.p.engine.begin() as conn:
            eid = self._insert(conn, code_n, data, active=active, actor_id=actor.id)
            audit(conn, C.LOG_EXERCICIO, "exercicio_criado", actor, target_type="exercicio", target_id=eid,
                  summary=f"Exercício {code_n} criado: {data['title']}")
            return self.get(eid, conn=conn)

    def _insert(self, conn, code_n: str, data: dict, *, active: bool, actor_id: str | None) -> str:
        """Inserção comum ao cadastro manual e à importação de pacotes."""
        if conn.execute(sa.select(db.exercises.c.id).where(db.exercises.c.code == code_n)).first():
            raise ValidationError(f"Já existe um exercício com o código {code_n}.", field="codigo")
        now = db.utcnow()
        eid = str(uuid.uuid4())
        conn.execute(
            db.exercises.insert().values(
                id=eid, code=code_n, active=bool(active), sort_key=exercise_sort_key(code_n),
                created_at=now, updated_at=now, created_by=actor_id, updated_by=actor_id, **data,
            )
        )
        return eid

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
            uploaded = [r[0] for r in conn.execute(
                sa.select(db.exercise_figures.c.ref).where(
                    db.exercise_figures.c.exercise_id == exercise_id, db.exercise_figures.c.source == FIG_ARQUIVO))]
            conn.execute(db.exercise_figures.delete().where(db.exercise_figures.c.exercise_id == exercise_id))
            conn.execute(db.exercises.delete().where(db.exercises.c.id == exercise_id))
            audit(conn, C.LOG_EXERCICIO, "exercicio_excluido", actor, target_type="exercicio", target_id=exercise_id,
                  summary=f"Exercício {cur.code} excluído (sem submissões)")
        for key in uploaded:
            self._delete_upload_if_orphan(key)

    # ------------------------------------------------------------------ #
    # Figuras (circuitos) dos exercícios
    # ------------------------------------------------------------------ #
    def figures(self, exercise_id: str) -> list[Figure]:
        """Figuras de um exercício, na ordem de exibição. Leitura pública:
        a visibilidade é a mesma do exercício em que a figura aparece."""
        with self.p.engine.connect() as conn:
            rows = conn.execute(
                sa.select(db.exercise_figures)
                .where(db.exercise_figures.c.exercise_id == exercise_id)
                .order_by(db.exercise_figures.c.position, db.exercise_figures.c.created_at)
            )
            return [_fig(r) for r in rows]

    def figure_bytes(self, fig: Figure) -> bytes:
        if fig.source == FIG_PACOTE:
            path = (CONTENT_ROOT / fig.ref).resolve()
            if CONTENT_ROOT.resolve() not in path.parents or not path.is_file():
                raise StorageFailure("A figura deste exercício não foi encontrada no pacote de conteúdo.")
            return path.read_bytes()
        return self.p.store.get(fig.ref)

    def _attach(self, conn, exercise_id: str, *, source: str, ref: str, label: str, caption: str,
                width: int | None, height: int | None) -> str:
        pos = conn.execute(
            sa.select(sa.func.coalesce(sa.func.max(db.exercise_figures.c.position), -1))
            .where(db.exercise_figures.c.exercise_id == exercise_id)
        ).scalar_one() + 1
        fid = str(uuid.uuid4())
        conn.execute(db.exercise_figures.insert().values(
            id=fid, exercise_id=exercise_id, position=pos, source=source, ref=ref, label=label[:120],
            caption=caption[:300], width=width, height=height, created_at=db.utcnow()))
        return fid

    def add_figure(self, actor: User, exercise_id: str, data: bytes, *, label: str = "", caption: str = "") -> Figure:
        """Anexa uma imagem enviada pela administração (PNG ou JPEG, até 5 MB)."""
        require_admin(actor)
        if not data:
            raise ValidationError("Selecione uma imagem.", field="figura")
        if len(data) > MAX_FIGURE_MB * 1024 * 1024:
            raise ValidationError(f"A imagem excede {MAX_FIGURE_MB} MB.", field="figura")
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(data))
            img.verify()
            img = Image.open(io.BytesIO(data))
            fmt, (w, h) = img.format, img.size
        except Exception as exc:
            raise ValidationError("O arquivo não é uma imagem válida (use PNG ou JPEG).", field="figura") from exc
        if fmt not in ("PNG", "JPEG"):
            raise ValidationError("Formato não suportado. Use PNG ou JPEG.", field="figura")
        ex = self.get(exercise_id)
        ext = "png" if fmt == "PNG" else "jpg"
        key = f"figuras/{exercise_id}/{uuid.uuid4().hex}.{ext}"
        self.p.store.put(key, data, content_type="image/png" if fmt == "PNG" else "image/jpeg")
        label = clean_text(label, max_len=120, field="rotulo", label="Rótulo")
        caption = clean_text(caption, max_len=300, field="legenda", label="Legenda")
        try:
            with self.p.engine.begin() as conn:
                fid = self._attach(conn, exercise_id, source=FIG_ARQUIVO, ref=key, label=label, caption=caption,
                                   width=w, height=h)
                audit(conn, C.LOG_EXERCICIO, "figura_adicionada", actor, target_type="exercicio", target_id=exercise_id,
                      summary=f"Figura adicionada ao exercício {ex.code}" + (f": {label}" if label else ""))
        except Exception:
            self.p.store.delete(key)
            raise
        return next(f for f in self.figures(exercise_id) if f.id == fid)

    def remove_figure(self, actor: User, figure_id: str) -> None:
        require_admin(actor)
        with self.p.engine.begin() as conn:
            row = conn.execute(sa.select(db.exercise_figures).where(db.exercise_figures.c.id == figure_id)).first()
            if row is None:
                raise NotFound("Figura não encontrada.")
            fig = _fig(row)
            ex = self.get(fig.exercise_id, conn=conn)
            conn.execute(db.exercise_figures.delete().where(db.exercise_figures.c.id == figure_id))
            audit(conn, C.LOG_EXERCICIO, "figura_removida", actor, target_type="exercicio", target_id=fig.exercise_id,
                  summary=f"Figura removida do exercício {ex.code}" + (f": {fig.label}" if fig.label else ""))
        if fig.source == FIG_ARQUIVO:
            self._delete_upload_if_orphan(fig.ref)

    def _delete_upload_if_orphan(self, key: str) -> None:
        try:
            with self.p.engine.connect() as conn:
                used = conn.execute(sa.select(sa.func.count()).select_from(db.exercise_figures)
                                    .where(db.exercise_figures.c.ref == key)).scalar_one()
            if not used:
                self.p.store.delete(key)
        except Exception:
            pass
