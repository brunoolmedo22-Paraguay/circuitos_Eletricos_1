"""Avaliação acadêmica, pareceres e publicação no catálogo.

A aprovação é a única porta de entrada no catálogo público. Não existem notas:
somente a decisão (aprovada/devolvida) e, na aprovação, um dos três níveis
oficiais.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

import sqlalchemy as sa

from .. import constants as C
from .. import db
from ..errors import ConflictError, NotFound, PermissionDenied, ValidationError
from ..parecer import build_parecer_pdf
from ..validators import parse_duration_text
from .common import User, audit, clean_text, require_admin, require_user, row_to_user
from .submissions import _m

log = logging.getLogger(__name__)

_CONFLICT_MSG = (
    "Esta submissão foi alterada por outro administrador enquanto você avaliava. "
    "Atualize a página para ver o estado atual."
)


class ReviewService:
    def __init__(self, platform):
        self.p = platform

    # ------------------------------------------------------------------ #
    # Bandeja
    # ------------------------------------------------------------------ #
    def inbox(
        self,
        actor: User,
        *,
        statuses: list[str] | None = None,
        exercise_id: str | None = None,
        student_q: str = "",
        unit: str | None = None,
        reviewer_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict]:
        require_admin(actor)
        author = db.users.alias("author")
        reviewer = db.users.alias("reviewer")
        stmt = (
            sa.select(
                db.submissions,
                db.exercises.c.code,
                db.exercises.c.title,
                db.exercises.c.unit,
                author.c.full_name.label("author_name"),
                author.c.matricula.label("author_matricula"),
                author.c.active.label("author_active"),
                reviewer.c.full_name.label("reviewer_name"),
            )
            .join(db.exercises, db.exercises.c.id == db.submissions.c.exercise_id)
            .join(author, author.c.id == db.submissions.c.author_id)
            .outerjoin(reviewer, reviewer.c.id == db.submissions.c.reviewer_id)
        )
        if statuses:
            stmt = stmt.where(db.submissions.c.status.in_(statuses))
        if exercise_id:
            stmt = stmt.where(db.submissions.c.exercise_id == exercise_id)
        if unit:
            stmt = stmt.where(db.exercises.c.unit == unit)
        if reviewer_id:
            stmt = stmt.where(db.submissions.c.reviewer_id == reviewer_id)
        if date_from:
            stmt = stmt.where(db.submissions.c.last_submitted_at >= date_from)
        if date_to:
            stmt = stmt.where(db.submissions.c.last_submitted_at <= date_to)
        # Pendentes mais antigos primeiro (fila justa).
        stmt = stmt.order_by(sa.func.coalesce(db.submissions.c.last_submitted_at, db.submissions.c.updated_at))
        with self.p.engine.connect() as conn:
            rows = [_m(r) for r in conn.execute(stmt)]
        if student_q:
            q = student_q.strip().lower()
            rows = [r for r in rows if q in f"{r['author_name']} {r['author_matricula'] or ''}".lower()]
        return rows

    def counts(self, actor: User) -> dict[str, int]:
        require_admin(actor)
        with self.p.engine.connect() as conn:
            rows = conn.execute(
                sa.select(db.submissions.c.status, sa.func.count()).group_by(db.submissions.c.status)
            )
            return {r[0]: r[1] for r in rows}

    # ------------------------------------------------------------------ #
    # Início / liberação da análise
    # ------------------------------------------------------------------ #
    def claim(self, actor: User, sid: str, *, expected_row_version: int, takeover: bool = False) -> None:
        require_admin(actor)
        with self.p.engine.begin() as conn:
            sub = self.p.submissions._sub(conn, sid)
            now = db.utcnow()
            if sub["status"] in C.PENDING_STATUSES:
                res = conn.execute(
                    db.submissions.update()
                    .where(
                        db.submissions.c.id == sid,
                        db.submissions.c.row_version == expected_row_version,
                        db.submissions.c.status.in_(list(C.PENDING_STATUSES)),
                    )
                    .values(
                        status=C.EM_ANALISE, reviewer_id=actor.id, review_started_at=now,
                        row_version=db.submissions.c.row_version + 1, updated_at=now,
                    )
                )
                if res.rowcount != 1:
                    raise ConflictError(_CONFLICT_MSG)
                audit(conn, C.LOG_SUBMISSAO, "analise_iniciada", actor, target_type="submissao", target_id=sid,
                      summary=f"Análise da v{sub['current_version_no']} iniciada")
            elif sub["status"] == C.EM_ANALISE and sub["reviewer_id"] != actor.id:
                if not takeover:
                    raise ConflictError("Outro administrador já está avaliando esta submissão.")
                res = conn.execute(
                    db.submissions.update()
                    .where(
                        db.submissions.c.id == sid,
                        db.submissions.c.row_version == expected_row_version,
                        db.submissions.c.status == C.EM_ANALISE,
                    )
                    .values(reviewer_id=actor.id, review_started_at=now, row_version=db.submissions.c.row_version + 1, updated_at=now)
                )
                if res.rowcount != 1:
                    raise ConflictError(_CONFLICT_MSG)
                audit(conn, C.LOG_SUBMISSAO, "analise_assumida", actor, target_type="submissao", target_id=sid,
                      summary="Análise assumida de outro administrador", anterior=sub["reviewer_id"])
            elif sub["status"] == C.EM_ANALISE:
                return
            else:
                raise ConflictError("Esta submissão não está aguardando avaliação.")

    def release(self, actor: User, sid: str, *, expected_row_version: int) -> None:
        require_admin(actor)
        with self.p.engine.begin() as conn:
            sub = self.p.submissions._sub(conn, sid)
            if sub["status"] != C.EM_ANALISE:
                raise ConflictError("Esta submissão não está em análise.")
            back = C.SUBMETIDA if sub["current_version_no"] == 1 else C.REENVIADA
            res = conn.execute(
                db.submissions.update()
                .where(db.submissions.c.id == sid, db.submissions.c.row_version == expected_row_version,
                       db.submissions.c.status == C.EM_ANALISE)
                .values(status=back, reviewer_id=None, review_started_at=None,
                        row_version=db.submissions.c.row_version + 1, updated_at=db.utcnow())
            )
            if res.rowcount != 1:
                raise ConflictError(_CONFLICT_MSG)
            audit(conn, C.LOG_SUBMISSAO, "analise_liberada", actor, target_type="submissao", target_id=sid,
                  summary="Análise interrompida; submissão devolvida à fila")

    # ------------------------------------------------------------------ #
    # Decisão
    # ------------------------------------------------------------------ #
    @staticmethod
    def _clean_criteria(criteria: dict) -> dict:
        out = {}
        for key, name in C.CRITERIA:
            item = (criteria or {}).get(key) or {}
            rating = item.get("rating")
            if rating not in C.RATINGS:
                raise ValidationError(f"Avalie o critério “{name}”.", field=f"criterio_{key}")
            comment = clean_text(item.get("comment"), max_len=1500, field=f"criterio_{key}", label=name)
            out[key] = {"rating": rating, "comment": comment}
        return out

    @staticmethod
    def _clean_requirements(req: dict) -> dict:
        return {k: bool((req or {}).get(k)) for k, _ in C.REQUIREMENTS}

    def _load_for_decision(self, conn, actor: User, sid: str, expected: int) -> tuple[dict, dict]:
        sub = self.p.submissions._sub(conn, sid)
        if sub["row_version"] != expected:
            raise ConflictError(_CONFLICT_MSG)
        if sub["status"] != C.EM_ANALISE:
            raise ConflictError("Inicie a análise antes de registrar a decisão.")
        if sub["reviewer_id"] != actor.id:
            raise ConflictError("Esta submissão está sendo avaliada por outro administrador. Assuma a análise antes de decidir.")
        ver = self.p.submissions._version(conn, sid, sub["current_version_no"])
        if ver is None or ver["state"] != C.V_ENVIADA:
            raise ConflictError("A versão atual não está disponível para avaliação.")
        return sub, ver

    def _payload(self, conn, *, sub, ver, review_id, reviewer: User, decision, level, requirements, criteria,
                 problems="", observations="", recommendations="", resubmit_instructions="", reviewed_at=None) -> dict:
        ex = self.p.exercises.get(sub["exercise_id"], conn=conn)
        author = row_to_user(conn.execute(sa.select(db.users).where(db.users.c.id == sub["author_id"])).first())
        return {
            "review_id": review_id,
            "institution": self.p.admin.get_setting("institution"),
            "course": self.p.admin.get_setting("course"),
            "student_name": author.full_name,
            "student_matricula": author.matricula,
            "coauthors": sub["coauthors"],
            "exercise_code": ex.code,
            "exercise_title": ex.title,
            "unit": ex.unit,
            "version_no": ver["version_no"],
            "submitted_at": ver["submitted_at"],
            "reviewed_at": reviewed_at or db.utcnow(),
            "reviewer_name": reviewer.full_name,
            "decision": decision,
            "level": level,
            "requirements": requirements,
            "criteria": criteria,
            "problems": problems,
            "observations": observations,
            "recommendations": recommendations,
            "resubmit_instructions": resubmit_instructions,
            "youtube_url": ver["youtube_url"],
            "falstad_url": ver["falstad_url"],
            "pdf_filename": ver["pdf_filename"],
        }

    def _store_parecer(self, sid: str, review_id: str, payload: dict) -> str:
        pdf = build_parecer_pdf(payload, tz=self.p.tz)
        key = f"pareceres/{sid}/{review_id}.pdf"
        self.p.store.put(key, pdf)
        return key

    def approve(
        self,
        actor: User,
        sid: str,
        *,
        expected_row_version: int,
        level: str,
        requirements: dict,
        criteria: dict,
        observations: str = "",
        recommendations: str = "",
        verified_duration: str = "",
    ) -> str:
        require_admin(actor)
        if level not in C.LEVELS:
            raise ValidationError("Selecione um dos três níveis oficiais de aprovação.", field="nivel")
        req = self._clean_requirements(requirements)
        if not all(req.values()):
            raise ValidationError(
                "Para aprovar, os três materiais obrigatórios (YouTube, PDF e Falstad) precisam estar cumpridos. "
                "Caso contrário, devolva para correção.",
                field="requisitos",
            )
        crit = self._clean_criteria(criteria)
        if any(v["rating"] == C.RATING_NAO_ATENDE for v in crit.values()):
            raise ValidationError(
                "Há critério marcado como “Não atende”. Uma resolução com critério não atendido deve ser devolvida para correção.",
                field="criterios",
            )
        observations = clean_text(observations, max_len=6000, field="observacoes", label="Observações")
        recommendations = clean_text(recommendations, max_len=6000, field="recomendacoes", label="Recomendações")
        duration = parse_duration_text(verified_duration)

        review_id = str(uuid.uuid4())
        now = db.utcnow()
        with self.p.engine.connect() as conn:
            sub, ver = self._load_for_decision(conn, actor, sid, expected_row_version)
            payload = self._payload(conn, sub=sub, ver=ver, review_id=review_id, reviewer=actor,
                                    decision=C.DECISION_APROVADA, level=level, requirements=req, criteria=crit,
                                    observations=observations, recommendations=recommendations, reviewed_at=now)
        key = self._store_parecer(sid, review_id, payload)
        try:
            with self.p.engine.begin() as conn:
                res = conn.execute(
                    db.submissions.update()
                    .where(
                        db.submissions.c.id == sid,
                        db.submissions.c.row_version == expected_row_version,
                        db.submissions.c.status == C.EM_ANALISE,
                        db.submissions.c.reviewer_id == actor.id,
                    )
                    .values(
                        status=C.APROVADA, is_published=True, published_version_id=ver["id"],
                        published_review_id=review_id, published_level=level, published_at=now,
                        first_approved_at=sa.func.coalesce(db.submissions.c.first_approved_at, now),
                        reviewer_id=None, review_started_at=None, retired_reason=None, resource_alert=None,
                        row_version=db.submissions.c.row_version + 1, updated_at=now,
                    )
                )
                if res.rowcount != 1:
                    raise ConflictError(_CONFLICT_MSG)
                vvals = {"state": C.V_APROVADA, "updated_at": now}
                if duration:
                    vvals.update(video_duration_s=duration, video_duration_source="verificada")
                conn.execute(db.versions.update().where(db.versions.c.id == ver["id"]).values(**vvals))
                conn.execute(
                    db.reviews.insert().values(
                        id=review_id, submission_id=sid, version_id=ver["id"], version_no=ver["version_no"],
                        reviewer_id=actor.id, kind=C.REVIEW_KIND_AVALIACAO, decision=C.DECISION_APROVADA,
                        level=level, previous_level=sub["published_level"],
                        requirements_json=json.dumps(req), criteria_json=json.dumps(crit, ensure_ascii=False),
                        problems="", observations=observations, recommendations=recommendations,
                        resubmit_instructions="", parecer_key=key, created_at=now,
                    )
                )
                summary = f"Exercício {payload['exercise_code']} v{ver['version_no']}: {C.LEVEL_LABELS[level]}"
                audit(conn, C.LOG_AVALIACAO, "aprovada", actor, target_type="submissao", target_id=sid,
                      summary=summary, nivel=level, versao=ver["version_no"], parecer=review_id)
                audit(conn, C.LOG_SUBMISSAO, "publicada" if not sub["published_version_id"] else "publicacao_atualizada",
                      actor, target_type="submissao", target_id=sid,
                      summary=f"Publicada no catálogo (v{ver['version_no']})")
        except Exception:
            self._discard(key)
            raise
        return review_id

    def return_for_correction(
        self,
        actor: User,
        sid: str,
        *,
        expected_row_version: int,
        requirements: dict,
        criteria: dict,
        problems: str,
        observations: str = "",
        recommendations: str = "",
        resubmit_instructions: str = "",
    ) -> str:
        require_admin(actor)
        req = self._clean_requirements(requirements)
        crit = self._clean_criteria(criteria)
        problems = clean_text(problems, max_len=6000, field="problemas", label="Problemas identificados", required=True)
        if len(problems) < 10:
            raise ValidationError("Descreva os problemas identificados de forma objetiva (ao menos uma frase).", field="problemas")
        observations = clean_text(observations, max_len=6000, field="observacoes", label="Observações")
        recommendations = clean_text(recommendations, max_len=6000, field="recomendacoes", label="Recomendações")
        resubmit_instructions = clean_text(resubmit_instructions, max_len=3000, field="reenvio", label="Indicações para o reenvio")

        review_id = str(uuid.uuid4())
        now = db.utcnow()
        with self.p.engine.connect() as conn:
            sub, ver = self._load_for_decision(conn, actor, sid, expected_row_version)
            payload = self._payload(conn, sub=sub, ver=ver, review_id=review_id, reviewer=actor,
                                    decision=C.DECISION_DEVOLVIDA, level=None, requirements=req, criteria=crit,
                                    problems=problems, observations=observations, recommendations=recommendations,
                                    resubmit_instructions=resubmit_instructions, reviewed_at=now)
        key = self._store_parecer(sid, review_id, payload)
        try:
            with self.p.engine.begin() as conn:
                res = conn.execute(
                    db.submissions.update()
                    .where(
                        db.submissions.c.id == sid,
                        db.submissions.c.row_version == expected_row_version,
                        db.submissions.c.status == C.EM_ANALISE,
                        db.submissions.c.reviewer_id == actor.id,
                    )
                    .values(status=C.DEVOLVIDA, reviewer_id=None, review_started_at=None,
                            row_version=db.submissions.c.row_version + 1, updated_at=now)
                )
                if res.rowcount != 1:
                    raise ConflictError(_CONFLICT_MSG)
                conn.execute(db.versions.update().where(db.versions.c.id == ver["id"]).values(state=C.V_DEVOLVIDA, updated_at=now))
                conn.execute(
                    db.reviews.insert().values(
                        id=review_id, submission_id=sid, version_id=ver["id"], version_no=ver["version_no"],
                        reviewer_id=actor.id, kind=C.REVIEW_KIND_AVALIACAO, decision=C.DECISION_DEVOLVIDA, level=None,
                        previous_level=sub["published_level"], requirements_json=json.dumps(req),
                        criteria_json=json.dumps(crit, ensure_ascii=False), problems=problems,
                        observations=observations, recommendations=recommendations,
                        resubmit_instructions=resubmit_instructions, parecer_key=key, created_at=now,
                    )
                )
                audit(conn, C.LOG_AVALIACAO, "devolvida", actor, target_type="submissao", target_id=sid,
                      summary=f"Exercício {payload['exercise_code']} v{ver['version_no']}: devolvida para correção",
                      versao=ver["version_no"], parecer=review_id)
        except Exception:
            self._discard(key)
            raise
        return review_id

    def _discard(self, key: str) -> None:
        try:
            self.p.store.delete(key)
        except Exception:
            log.warning("Parecer órfão não removido: %s", key)

    # ------------------------------------------------------------------ #
    # Publicação: retirar, restaurar, ajustar nível
    # ------------------------------------------------------------------ #
    def retire(self, actor: User, sid: str, *, expected_row_version: int, reason: str) -> None:
        require_admin(actor)
        reason = clean_text(reason, max_len=2000, field="motivo", label="Motivo da retirada", required=True)
        with self.p.engine.begin() as conn:
            sub = self.p.submissions._sub(conn, sid)
            if not sub["is_published"]:
                raise ConflictError("Esta resolução não está publicada.")
            if sub["status"] not in (C.APROVADA, C.DEVOLVIDA):
                raise ConflictError(
                    "Há uma versão aguardando avaliação ou em análise. Conclua a avaliação dessa versão antes de retirar a publicação."
                )
            res = conn.execute(
                db.submissions.update()
                .where(db.submissions.c.id == sid, db.submissions.c.row_version == expected_row_version)
                .values(is_published=False, status=C.RETIRADA, retired_reason=reason,
                        row_version=db.submissions.c.row_version + 1, updated_at=db.utcnow())
            )
            if res.rowcount != 1:
                raise ConflictError(_CONFLICT_MSG)
            audit(conn, C.LOG_SUBMISSAO, "publicacao_retirada", actor, target_type="submissao", target_id=sid,
                  summary="Publicação retirada do catálogo", motivo=reason)

    def restore(self, actor: User, sid: str, *, expected_row_version: int) -> None:
        require_admin(actor)
        with self.p.engine.begin() as conn:
            sub = self.p.submissions._sub(conn, sid)
            if sub["is_published"] or not sub["published_version_id"]:
                raise ConflictError("Não há publicação retirada para restaurar.")
            if sub["status"] != C.RETIRADA:
                raise ConflictError("Há uma versão nova em andamento. Avalie-a; se aprovada, ela será publicada.")
            latest = self.p.submissions._version(conn, sid, sub["current_version_no"])
            prev = latest
            if latest["state"] == C.V_RASCUNHO:
                prev = self.p.submissions._version(conn, sid, sub["current_version_no"] - 1)
            new_status = C.DEVOLVIDA if prev and prev["state"] == C.V_DEVOLVIDA else C.APROVADA
            res = conn.execute(
                db.submissions.update()
                .where(db.submissions.c.id == sid, db.submissions.c.row_version == expected_row_version)
                .values(is_published=True, status=new_status, retired_reason=None,
                        row_version=db.submissions.c.row_version + 1, updated_at=db.utcnow())
            )
            if res.rowcount != 1:
                raise ConflictError(_CONFLICT_MSG)
            audit(conn, C.LOG_SUBMISSAO, "publicacao_restaurada", actor, target_type="submissao", target_id=sid,
                  summary="Publicação restaurada no catálogo")

    def change_level(self, actor: User, sid: str, *, expected_row_version: int, level: str, justification: str) -> None:
        require_admin(actor)
        if level not in C.LEVELS:
            raise ValidationError("Selecione um dos três níveis oficiais.", field="nivel")
        justification = clean_text(justification, max_len=3000, field="justificativa", label="Justificativa", required=True)
        now = db.utcnow()
        with self.p.engine.begin() as conn:
            sub = self.p.submissions._sub(conn, sid)
            if not sub["published_version_id"]:
                raise ConflictError("Somente resoluções aprovadas possuem nível.")
            if sub["published_level"] == level:
                raise ValidationError("O nível selecionado é igual ao atual.", field="nivel")
            res = conn.execute(
                db.submissions.update()
                .where(db.submissions.c.id == sid, db.submissions.c.row_version == expected_row_version)
                .values(published_level=level, row_version=db.submissions.c.row_version + 1, updated_at=now)
            )
            if res.rowcount != 1:
                raise ConflictError(_CONFLICT_MSG)
            ver = _m(conn.execute(sa.select(db.versions).where(db.versions.c.id == sub["published_version_id"])).first())
            conn.execute(
                db.reviews.insert().values(
                    id=str(uuid.uuid4()), submission_id=sid, version_id=ver["id"], version_no=ver["version_no"],
                    reviewer_id=actor.id, kind=C.REVIEW_KIND_AJUSTE, decision=C.DECISION_APROVADA, level=level,
                    previous_level=sub["published_level"], requirements_json="{}", criteria_json="{}",
                    problems="", observations=justification, recommendations="", resubmit_instructions="",
                    parecer_key=None, created_at=now,
                )
            )
            audit(conn, C.LOG_AVALIACAO, "nivel_alterado", actor, target_type="submissao", target_id=sid,
                  summary=f"Nível alterado: {C.LEVEL_SHORT.get(sub['published_level'])} → {C.LEVEL_SHORT[level]}",
                  justificativa=justification)

    # ------------------------------------------------------------------ #
    # Histórico e pareceres
    # ------------------------------------------------------------------ #
    def history(self, actor: User, *, decision: str | None = None, reviewer_id: str | None = None,
                exercise_id: str | None = None, q: str = "") -> list[dict]:
        require_admin(actor)
        author = db.users.alias("author")
        reviewer = db.users.alias("reviewer")
        stmt = (
            sa.select(
                db.reviews,
                db.exercises.c.code,
                db.exercises.c.title,
                author.c.full_name.label("author_name"),
                reviewer.c.full_name.label("reviewer_name"),
            )
            .join(db.submissions, db.submissions.c.id == db.reviews.c.submission_id)
            .join(db.exercises, db.exercises.c.id == db.submissions.c.exercise_id)
            .join(author, author.c.id == db.submissions.c.author_id)
            .join(reviewer, reviewer.c.id == db.reviews.c.reviewer_id)
            .order_by(db.reviews.c.created_at.desc())
        )
        if decision:
            stmt = stmt.where(db.reviews.c.decision == decision)
        if reviewer_id:
            stmt = stmt.where(db.reviews.c.reviewer_id == reviewer_id)
        if exercise_id:
            stmt = stmt.where(db.submissions.c.exercise_id == exercise_id)
        with self.p.engine.connect() as conn:
            rows = [_m(r) for r in conn.execute(stmt)]
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in f"{r['author_name']} {r['code']} {r['title']}".lower()]
        return rows

    def parecer_pdf(self, actor: User, review_id: str) -> tuple[bytes, str]:
        require_user(actor)
        with self.p.engine.connect() as conn:
            rev = _m(conn.execute(sa.select(db.reviews).where(db.reviews.c.id == review_id)).first())
            if rev is None:
                raise NotFound("Parecer não encontrado.")
            sub = self.p.submissions._sub(conn, rev["submission_id"])
            ex = self.p.exercises.get(sub["exercise_id"], conn=conn)
        if not (actor.is_admin or actor.id == sub["author_id"]):
            raise NotFound("Parecer não encontrado.")
        if not rev["parecer_key"]:
            raise NotFound("Este registro não possui parecer em PDF.")
        data = self.p.store.get(rev["parecer_key"])
        kind = "Aprovacao" if rev["decision"] == C.DECISION_APROVADA else "Devolucao"
        return data, f"Parecer_{kind}_Exercicio_{ex.code}_v{rev['version_no']}.pdf"

    def regenerate_parecer(self, actor: User, review_id: str) -> None:
        """Recria o PDF a partir dos dados gravados (ex.: arquivo perdido no armazenamento)."""
        require_admin(actor)
        with self.p.engine.connect() as conn:
            rev = _m(conn.execute(sa.select(db.reviews).where(db.reviews.c.id == review_id)).first())
            if rev is None or rev["kind"] != C.REVIEW_KIND_AVALIACAO:
                raise NotFound("Parecer não encontrado.")
            sub = self.p.submissions._sub(conn, rev["submission_id"])
            ver = _m(conn.execute(sa.select(db.versions).where(db.versions.c.id == rev["version_id"])).first())
            reviewer = row_to_user(conn.execute(sa.select(db.users).where(db.users.c.id == rev["reviewer_id"])).first())
            payload = self._payload(
                conn, sub=sub, ver=ver, review_id=review_id, reviewer=reviewer, decision=rev["decision"],
                level=rev["level"], requirements=json.loads(rev["requirements_json"] or "{}"),
                criteria=json.loads(rev["criteria_json"] or "{}"), problems=rev["problems"],
                observations=rev["observations"], recommendations=rev["recommendations"],
                resubmit_instructions=rev["resubmit_instructions"], reviewed_at=rev["created_at"],
            )
        key = self._store_parecer(rev["submission_id"], review_id, payload)
        with self.p.engine.begin() as conn:
            conn.execute(db.reviews.update().where(db.reviews.c.id == review_id).values(parecer_key=key))
            audit(conn, C.LOG_AVALIACAO, "parecer_regenerado", actor, target_type="parecer", target_id=review_id,
                  summary="Parecer em PDF regenerado a partir do registro da avaliação")

    def preview_parecer(self, actor: User, sid: str, *, decision: str, level: str | None, requirements: dict,
                        criteria: dict, problems="", observations="", recommendations="", resubmit_instructions="") -> bytes:
        """Gera o parecer em memória (sem gravar) para conferência antes da decisão."""
        require_admin(actor)
        crit = {k: (criteria or {}).get(k) or {} for k, _ in C.CRITERIA}
        with self.p.engine.connect() as conn:
            sub = self.p.submissions._sub(conn, sid)
            ver = self.p.submissions._version(conn, sid, sub["current_version_no"])
            payload = self._payload(conn, sub=sub, ver=ver, review_id="previa", reviewer=actor, decision=decision,
                                    level=level, requirements=self._clean_requirements(requirements), criteria=crit,
                                    problems=problems, observations=observations, recommendations=recommendations,
                                    resubmit_instructions=resubmit_instructions)
        return build_parecer_pdf(payload, tz=self.p.tz)
