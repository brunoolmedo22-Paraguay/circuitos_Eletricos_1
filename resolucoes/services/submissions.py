"""Submissões dos alunos, rascunhos e controle de versões.

Regras centrais:

* Cada aluno possui no máximo uma submissão por exercício; tentativas
  posteriores tornam-se novas **versões** da mesma submissão.
* Uma versão enviada é imutável. Correções sempre geram uma nova versão.
* Durante a avaliação (``EM_ANALISE``) nada pode ser alterado pelo aluno.
* Uma nova versão de uma resolução aprovada **não** substitui a publicação:
  a versão aprovada continua no catálogo até que a nova seja aprovada.
* Toda alteração usa controle otimista (``row_version``) para impedir envios
  duplicados e alterações concorrentes silenciosas.
"""

from __future__ import annotations

import logging
import uuid

import sqlalchemy as sa

from .. import constants as C
from .. import db
from ..errors import ConflictError, NotFound, PermissionDenied, StorageFailure, ValidationError
from ..validators import (
    check_youtube_video,
    format_duration,
    parse_duration_text,
    parse_youtube_id,
    safe_filename,
    validate_falstad_url,
    validate_pdf,
    video_check_error,
    watch_url,
)
from .common import User, audit, clean_text, require_student, require_user, row_to_user

log = logging.getLogger(__name__)


def _m(row) -> dict:
    return dict(row._mapping) if row is not None else None


class SubmissionService:
    def __init__(self, platform):
        self.p = platform

    # ------------------------------------------------------------------ #
    # Leitura interna
    # ------------------------------------------------------------------ #
    def _sub(self, conn, sid: str) -> dict:
        row = conn.execute(sa.select(db.submissions).where(db.submissions.c.id == sid)).first()
        if row is None:
            raise NotFound("Submissão não encontrada.")
        return _m(row)

    def _version(self, conn, sid: str, no: int) -> dict | None:
        return _m(
            conn.execute(
                sa.select(db.versions).where(db.versions.c.submission_id == sid, db.versions.c.version_no == no)
            ).first()
        )

    def _versions(self, conn, sid: str) -> list[dict]:
        return [
            _m(r)
            for r in conn.execute(
                sa.select(db.versions).where(db.versions.c.submission_id == sid).order_by(db.versions.c.version_no)
            )
        ]

    def _pdf_refcount(self, conn, key: str) -> int:
        n = conn.execute(sa.select(sa.func.count()).select_from(db.versions).where(db.versions.c.pdf_key == key)).scalar_one()
        return n

    @staticmethod
    def _check_owner(actor: User, sub: dict) -> None:
        if sub["author_id"] != actor.id:
            raise PermissionDenied("Você só pode alterar as suas próprias submissões.")

    @staticmethod
    def _check_row_version(sub: dict, expected: int | None) -> None:
        if expected is not None and sub["row_version"] != expected:
            raise ConflictError(
                "Esta submissão foi alterada em outra janela ou por outra pessoa. Atualize a página e tente novamente."
            )

    def _bump(self, conn, sid: str, expected: int, *, allowed_status=None, **values) -> None:
        stmt = db.submissions.update().where(db.submissions.c.id == sid, db.submissions.c.row_version == expected)
        if allowed_status:
            stmt = stmt.where(db.submissions.c.status.in_(list(allowed_status)))
        res = conn.execute(
            stmt.values(row_version=db.submissions.c.row_version + 1, updated_at=db.utcnow(), **values)
        )
        if res.rowcount != 1:
            raise ConflictError(
                "Esta submissão foi alterada em outra janela ou por outra pessoa. Atualize a página e tente novamente."
            )

    def _delete_file_if_orphan(self, key: str | None) -> None:
        if not key:
            return
        try:
            with self.p.engine.connect() as conn:
                if self._pdf_refcount(conn, key) == 0:
                    self.p.store.delete(key)
        except Exception:  # limpeza é best effort; a verificação de integridade lista órfãos
            log.warning("Não foi possível remover arquivo órfão %s", key)

    @staticmethod
    def resting_status(sub: dict, prev_state: str | None) -> str:
        """Estado administrativo quando não há versão pendente de avaliação."""
        if prev_state is None:
            return C.RASCUNHO
        if sub["published_version_id"] and not sub["is_published"]:
            return C.RETIRADA
        if prev_state == C.V_APROVADA:
            return C.APROVADA
        return C.DEVOLVIDA

    # ------------------------------------------------------------------ #
    # Criação e rascunho
    # ------------------------------------------------------------------ #
    def start(self, actor: User, exercise_id: str) -> str:
        """Abre (ou reabre) a submissão do aluno para um exercício. Retorna o id."""
        require_student(actor)
        with self.p.engine.begin() as conn:
            ex = self.p.exercises.get(exercise_id, conn=conn)
            existing = conn.execute(
                sa.select(db.submissions.c.id).where(
                    db.submissions.c.exercise_id == exercise_id, db.submissions.c.author_id == actor.id
                )
            ).first()
            if existing:
                return existing[0]
            if not ex.active:
                raise ValidationError("Este exercício não está disponível para novas entregas.")
            now = db.utcnow()
            sid = str(uuid.uuid4())
            conn.execute(
                db.submissions.insert().values(
                    id=sid, exercise_id=exercise_id, author_id=actor.id, coauthors="", status=C.RASCUNHO,
                    current_version_no=1, is_published=False, row_version=1, created_at=now, updated_at=now,
                )
            )
            conn.execute(
                db.versions.insert().values(
                    id=str(uuid.uuid4()), submission_id=sid, version_no=1, state=C.V_RASCUNHO,
                    student_notes="", created_at=now, updated_at=now,
                )
            )
            audit(conn, C.LOG_SUBMISSAO, "rascunho_criado", actor, target_type="submissao", target_id=sid,
                  summary=f"Rascunho criado para o exercício {ex.code}")
            return sid

    def save_draft(
        self,
        actor: User,
        sid: str,
        *,
        expected_row_version: int,
        youtube_url: str = "",
        falstad_url: str = "",
        coauthors: str = "",
        notes: str = "",
        duration_text: str = "",
        pdf_bytes: bytes | None = None,
        pdf_name: str | None = None,
    ) -> dict:
        require_student(actor)
        # Validações de formato (sem rede) — campos vazios são permitidos no rascunho.
        yt_url = (youtube_url or "").strip()
        yt_id = parse_youtube_id(yt_url) if yt_url else None
        fal = validate_falstad_url(falstad_url) if (falstad_url or "").strip() else None
        duration = parse_duration_text(duration_text)
        coauthors = clean_text(coauthors, max_len=400, field="coautores", label="Coautores")
        notes = clean_text(notes, max_len=3000, field="observacoes", label="Observações para o avaliador")

        with self.p.engine.connect() as conn:
            sub = self._sub(conn, sid)
            self._check_owner(actor, sub)
            self._check_row_version(sub, expected_row_version)
            ver = self._version(conn, sid, sub["current_version_no"])
        if ver is None or ver["state"] != C.V_RASCUNHO:
            raise ConflictError("Esta versão já foi enviada e não pode mais ser editada. Prepare uma nova versão.")

        new_key = info = None
        if pdf_bytes is not None:
            info = validate_pdf(pdf_bytes, max_mb=float(self.p.admin.get_setting("max_pdf_mb")))
            new_key = f"resolucoes/{sid}/v{ver['version_no']}/{uuid.uuid4().hex}.pdf"
            self.p.store.put(new_key, pdf_bytes)  # StorageFailure interrompe antes de tocar no banco

        values = dict(
            youtube_url=yt_url or None,
            youtube_id=yt_id,
            falstad_url=fal,
            student_notes=notes,
            updated_at=db.utcnow(),
        )
        if yt_id != ver["youtube_id"]:
            values.update(youtube_title=None, youtube_channel=None, video_check=None, video_checked_at=None)
            if ver["video_duration_source"] == "api":
                values.update(video_duration_s=None, video_duration_source=None)
        if duration is not None:
            values.update(video_duration_s=duration, video_duration_source="declarada")
        elif ver["video_duration_source"] == "declarada":
            values.update(video_duration_s=None, video_duration_source=None)
        if new_key:
            values.update(
                pdf_key=new_key, pdf_filename=safe_filename(pdf_name or "resolucao.pdf"),
                pdf_size=info.size, pdf_pages=info.pages, pdf_sha256=info.sha256,
            )
        try:
            with self.p.engine.begin() as conn:
                self._bump(conn, sid, expected_row_version, coauthors=coauthors)
                conn.execute(
                    db.versions.update().where(db.versions.c.id == ver["id"], db.versions.c.state == C.V_RASCUNHO).values(**values)
                )
                audit(conn, C.LOG_SUBMISSAO, "rascunho_salvo", actor, target_type="submissao", target_id=sid,
                      summary=f"Rascunho v{ver['version_no']} salvo" + (" com novo PDF" if new_key else ""),
                      pdf_novo=bool(new_key))
        except Exception:
            if new_key:
                try:
                    self.p.store.delete(new_key)
                except Exception:
                    pass
            raise
        if new_key and ver["pdf_key"] and ver["pdf_key"] != new_key:
            self._delete_file_if_orphan(ver["pdf_key"])
        return self.detail(actor, sid)

    # ------------------------------------------------------------------ #
    # Envio para avaliação
    # ------------------------------------------------------------------ #
    def submit(self, actor: User, sid: str, *, expected_row_version: int, declaration: bool) -> list[str]:
        """Envia a versão em rascunho. Retorna avisos não bloqueantes."""
        require_student(actor)
        with self.p.engine.connect() as conn:
            sub = self._sub(conn, sid)
            self._check_owner(actor, sub)
            ver = self._version(conn, sid, sub["current_version_no"])
            ex = self.p.exercises.get(sub["exercise_id"], conn=conn)
        if ver is None or ver["state"] != C.V_RASCUNHO:
            raise ConflictError("Esta versão já foi enviada. Acompanhe o estado em “Minhas Submissões”.")
        self._check_row_version(sub, expected_row_version)
        if sub["current_version_no"] == 1 and not ex.active:
            raise ValidationError("Este exercício foi desativado e não aceita novas entregas.")

        missing = []
        if not ver["youtube_id"]:
            missing.append("link do vídeo no YouTube")
        if not ver["pdf_key"]:
            missing.append("arquivo PDF da resolução")
        if not ver["falstad_url"]:
            missing.append("link do circuito no Falstad")
        if missing:
            raise ValidationError("Entrega incompleta. Falta: " + ", ".join(missing) + ".")
        if not declaration:
            raise ValidationError("Confirme a declaração de autoria e a autorização de publicação.", field="declaracao")
        parse_youtube_id(ver["youtube_url"])
        validate_falstad_url(ver["falstad_url"])
        try:
            if not self.p.store.exists(ver["pdf_key"]):
                raise ValidationError("O PDF não foi encontrado no armazenamento. Envie o arquivo novamente e salve o rascunho.")
        except StorageFailure:
            raise StorageFailure("Não foi possível confirmar o PDF no armazenamento. Tente enviar novamente em instantes.")

        warnings: list[str] = []
        video_vals: dict = {}
        if self.p.settings.check_video_online:
            check = check_youtube_video(ver["youtube_id"], api_key=self.p.settings.youtube_api_key, http_get=self.p.http_get)
            err = video_check_error(check)
            if err:
                raise ValidationError(err, field="youtube")
            video_vals = dict(
                video_check=check.status, video_checked_at=db.utcnow(),
                youtube_title=(check.title or None) and check.title[:300],
                youtube_channel=(check.channel or None) and check.channel[:200],
            )
            if check.duration_s:
                video_vals.update(video_duration_s=check.duration_s, video_duration_source="api")
            if check.status == C.VIDEO_NAO_VERIFICADO:
                warnings.append("Não foi possível confirmar o vídeo no YouTube agora; o administrador o conferirá na revisão.")
        else:
            video_vals = dict(video_check=C.VIDEO_NAO_VERIFICADO, video_checked_at=db.utcnow())

        duration = video_vals.get("video_duration_s") or ver["video_duration_s"]
        if not duration:
            raise ValidationError("Informe a duração do vídeo (mm:ss).", field="duracao")
        max_min = float(self.p.admin.get_setting("max_video_minutes"))
        if duration > max_min * 60:
            warnings.append(
                f"O vídeo tem {format_duration(duration)}, acima da duração recomendada de {max_min:g} minutos. "
                "A administração avaliará se a explicação está adequada."
            )

        now = db.utcnow()
        new_status = C.SUBMETIDA if sub["current_version_no"] == 1 else C.REENVIADA
        with self.p.engine.begin() as conn:
            self._bump(
                conn, sid, expected_row_version,
                allowed_status=(C.RASCUNHO, C.DEVOLVIDA, C.APROVADA, C.RETIRADA),
                status=new_status, last_submitted_at=now,
                first_submitted_at=sa.func.coalesce(db.submissions.c.first_submitted_at, now),
                reviewer_id=None, review_started_at=None,
            )
            res = conn.execute(
                db.versions.update().where(db.versions.c.id == ver["id"], db.versions.c.state == C.V_RASCUNHO).values(
                    state=C.V_ENVIADA, submitted_at=now, updated_at=now, **video_vals
                )
            )
            if res.rowcount != 1:
                raise ConflictError("Esta versão já foi enviada.")
            action = "submissao_enviada" if new_status == C.SUBMETIDA else "reenvio"
            audit(conn, C.LOG_SUBMISSAO, action, actor, target_type="submissao", target_id=sid,
                  summary=f"Exercício {ex.code}: versão v{ver['version_no']} enviada para avaliação",
                  versao=ver["version_no"], video=video_vals.get("video_check"))
        return warnings

    def withdraw(self, actor: User, sid: str, *, expected_row_version: int) -> None:
        """Cancela o envio antes do início da análise (a versão volta a ser rascunho)."""
        require_student(actor)
        with self.p.engine.begin() as conn:
            sub = self._sub(conn, sid)
            self._check_owner(actor, sub)
            if sub["status"] not in C.PENDING_STATUSES:
                raise ConflictError("O envio só pode ser cancelado enquanto a avaliação não começou.")
            ver = self._version(conn, sid, sub["current_version_no"])
            prev = self._version(conn, sid, sub["current_version_no"] - 1)
            new_status = self.resting_status(sub, prev["state"] if prev else None)
            self._bump(conn, sid, expected_row_version, allowed_status=C.PENDING_STATUSES, status=new_status)
            conn.execute(
                db.versions.update().where(db.versions.c.id == ver["id"]).values(
                    state=C.V_RASCUNHO, submitted_at=None, updated_at=db.utcnow()
                )
            )
            audit(conn, C.LOG_SUBMISSAO, "envio_cancelado", actor, target_type="submissao", target_id=sid,
                  summary=f"Envio da v{ver['version_no']} cancelado pelo aluno antes da análise")

    def new_version(self, actor: User, sid: str, *, expected_row_version: int) -> None:
        """Cria um rascunho v(n+1) copiando os materiais da versão anterior."""
        require_student(actor)
        with self.p.engine.begin() as conn:
            sub = self._sub(conn, sid)
            self._check_owner(actor, sub)
            if sub["status"] not in C.NEW_VERSION_FROM:
                raise ConflictError("Uma nova versão só pode ser preparada após a avaliação da versão atual.")
            cur = self._version(conn, sid, sub["current_version_no"])
            if cur["state"] == C.V_RASCUNHO:
                return
            n = sub["current_version_no"] + 1
            self._bump(conn, sid, expected_row_version, allowed_status=C.NEW_VERSION_FROM, current_version_no=n)
            now = db.utcnow()
            copy_cols = (
                "youtube_url", "youtube_id", "youtube_title", "youtube_channel", "video_duration_s",
                "video_duration_source", "falstad_url", "pdf_key", "pdf_filename", "pdf_size", "pdf_pages",
                "pdf_sha256", "student_notes",
            )
            conn.execute(
                db.versions.insert().values(
                    id=str(uuid.uuid4()), submission_id=sid, version_no=n, state=C.V_RASCUNHO,
                    created_at=now, updated_at=now, **{c: cur[c] for c in copy_cols},
                )
            )
            audit(conn, C.LOG_SUBMISSAO, "nova_versao_criada", actor, target_type="submissao", target_id=sid,
                  summary=f"Rascunho da versão v{n} criado a partir da v{n - 1}")

    def discard_draft(self, actor: User, sid: str, *, expected_row_version: int) -> bool:
        """Descarta o rascunho atual. Retorna True se a submissão inteira foi excluída."""
        require_student(actor)
        removed_keys: list[str] = []
        deleted_all = False
        with self.p.engine.begin() as conn:
            sub = self._sub(conn, sid)
            self._check_owner(actor, sub)
            ver = self._version(conn, sid, sub["current_version_no"])
            if ver is None or ver["state"] != C.V_RASCUNHO or sub["status"] in C.PENDING_STATUSES + (C.EM_ANALISE,):
                raise ConflictError("Somente rascunhos podem ser descartados.")
            self._check_row_version(sub, expected_row_version)
            if ver["pdf_key"]:
                removed_keys.append(ver["pdf_key"])
            if sub["current_version_no"] == 1 and sub["first_submitted_at"] is None:
                conn.execute(db.versions.delete().where(db.versions.c.submission_id == sid))
                conn.execute(db.submissions.delete().where(db.submissions.c.id == sid))
                deleted_all = True
                summary = "Rascunho nunca enviado excluído pelo aluno"
            else:
                conn.execute(db.versions.delete().where(db.versions.c.id == ver["id"]))
                self._bump(conn, sid, expected_row_version, current_version_no=sub["current_version_no"] - 1)
                summary = f"Rascunho da v{ver['version_no']} descartado"
            audit(conn, C.LOG_SUBMISSAO, "rascunho_descartado", actor, target_type="submissao", target_id=sid, summary=summary)
        for key in removed_keys:
            self._delete_file_if_orphan(key)
        return deleted_all

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #
    def detail(self, actor: User, sid: str) -> dict:
        require_user(actor)
        with self.p.engine.connect() as conn:
            sub = self._sub(conn, sid)
            if not actor.is_admin and sub["author_id"] != actor.id:
                raise NotFound("Submissão não encontrada.")
            ex = self.p.exercises.get(sub["exercise_id"], conn=conn)
            author = row_to_user(conn.execute(sa.select(db.users).where(db.users.c.id == sub["author_id"])).first())
            versions = self._versions(conn, sid)
            reviews = [
                _m(r)
                for r in conn.execute(
                    sa.select(db.reviews, db.users.c.full_name.label("reviewer_name"))
                    .join(db.users, db.users.c.id == db.reviews.c.reviewer_id)
                    .where(db.reviews.c.submission_id == sid)
                    .order_by(db.reviews.c.created_at.desc())
                )
            ]
            reviewer = None
            if sub["reviewer_id"]:
                r = conn.execute(sa.select(db.users.c.full_name).where(db.users.c.id == sub["reviewer_id"])).first()
                reviewer = r[0] if r else None
        current = versions[-1] if versions else None
        published = next((v for v in versions if v["id"] == sub["published_version_id"]), None)
        return {
            "submission": sub,
            "exercise": ex,
            "author": author,
            "versions": versions,
            "current": current,
            "published": published,
            "reviews": reviews,
            "reviewer_name": reviewer,
        }

    def mine(self, actor: User) -> list[dict]:
        require_student(actor)
        stmt = (
            sa.select(
                db.submissions,
                db.exercises.c.code,
                db.exercises.c.title,
                db.exercises.c.unit,
            )
            .join(db.exercises, db.exercises.c.id == db.submissions.c.exercise_id)
            .where(db.submissions.c.author_id == actor.id)
            .order_by(db.submissions.c.updated_at.desc())
        )
        with self.p.engine.connect() as conn:
            rows = [_m(r) for r in conn.execute(stmt)]
            for r in rows:
                cur = self._version(conn, r["id"], r["current_version_no"])
                r["current_state"] = cur["state"] if cur else None
        return rows

    # ------------------------------------------------------------------ #
    # Arquivos (com verificação de permissão)
    # ------------------------------------------------------------------ #
    def version_pdf(self, actor: User | None, version_id: str) -> tuple[bytes, str]:
        with self.p.engine.connect() as conn:
            ver = _m(conn.execute(sa.select(db.versions).where(db.versions.c.id == version_id)).first())
            if ver is None or not ver["pdf_key"]:
                raise NotFound("Arquivo não encontrado.")
            sub = self._sub(conn, ver["submission_id"])
            ex = self.p.exercises.get(sub["exercise_id"], conn=conn)
        is_public = bool(sub["is_published"]) and sub["published_version_id"] == version_id
        allowed = is_public or (actor is not None and actor.active and (actor.is_admin or actor.id == sub["author_id"]))
        if not allowed:
            raise NotFound("Arquivo não encontrado.")
        data = self.p.store.get(ver["pdf_key"])
        return data, f"Exercicio_{ex.code}_v{ver['version_no']}.pdf"

    def youtube_watch_url(self, version: dict) -> str | None:
        return watch_url(version["youtube_id"]) if version and version.get("youtube_id") else None
