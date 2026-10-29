"""Configurações, logs, exportações, backup e verificação de integridade."""

from __future__ import annotations

import csv
import io
import json
import threading
import time
import zipfile
from datetime import datetime

import sqlalchemy as sa

from .. import constants as C
from .. import db
from ..errors import StorageFailure, ValidationError
from ..validators import check_youtube_video, validate_falstad_url
from .common import User, audit, clean_text, require_admin

BACKUP_TABLES = [db.users, db.exercises, db.exercise_figures, db.submissions, db.versions, db.reviews, db.audit_log, db.app_settings]


def _json_default(o):
    if isinstance(o, datetime):
        return o.isoformat()
    if isinstance(o, (bytes, bytearray, memoryview)):
        return None
    return str(o)


def to_csv(rows: list[dict], columns: list[tuple[str, str]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow([label for _, label in columns])
    for r in rows:
        w.writerow([_json_default(r.get(k)) if isinstance(r.get(k), datetime) else (r.get(k) if r.get(k) is not None else "") for k, _ in columns])
    return buf.getvalue().encode("utf-8-sig")  # BOM: abre corretamente no Excel


class AdminService:
    def __init__(self, platform):
        self.p = platform
        self._cache: dict = {}
        self._cache_at = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Configurações acadêmicas e operacionais
    # ------------------------------------------------------------------ #
    def _load_settings(self) -> dict:
        with self._lock:
            if time.monotonic() - self._cache_at < 30 and self._cache:
                return self._cache
            data = dict(C.DEFAULT_SETTINGS)
            with self.p.engine.connect() as conn:
                for k, v in conn.execute(sa.select(db.app_settings.c.key, db.app_settings.c.value_json)):
                    if k.startswith("_"):
                        continue
                    try:
                        data[k] = json.loads(v)
                    except Exception:
                        pass
            self._cache, self._cache_at = data, time.monotonic()
            return data

    def get_setting(self, key: str):
        return self._load_settings().get(key, C.DEFAULT_SETTINGS.get(key))

    def all_settings(self, actor: User) -> dict:
        require_admin(actor)
        return dict(self._load_settings())

    def update_settings(self, actor: User, values: dict) -> None:
        require_admin(actor)
        clean: dict = {}
        if "max_pdf_mb" in values:
            v = float(values["max_pdf_mb"])
            if not 1 <= v <= C.HARD_MAX_PDF_MB:
                raise ValidationError(f"O limite do PDF deve estar entre 1 e {C.HARD_MAX_PDF_MB} MB.")
            clean["max_pdf_mb"] = v
        if "max_video_minutes" in values:
            v = float(values["max_video_minutes"])
            if not 1 <= v <= 60:
                raise ValidationError("A duração recomendada deve estar entre 1 e 60 minutos.")
            clean["max_video_minutes"] = v
        if "self_registration_code" in values:
            code = (values["self_registration_code"] or "").strip()
            if code and len(code) < 6:
                raise ValidationError("O código da turma deve ter ao menos 6 caracteres (ou ficar vazio para desativar).")
            clean["self_registration_code"] = code
        for key, label in (("institution", "Instituição"), ("course", "Disciplina"), ("semester", "Semestre"),
                           ("professor", "Professor(a) responsável"), ("app_url", "Endereço público")):
            if key in values:
                clean[key] = clean_text(values[key], max_len=200, field=key, label=label)
        if "units" in values:
            units = [u.strip() for u in values["units"] if u and u.strip()]
            if not units:
                raise ValidationError("Cadastre ao menos uma unidade ou tema.")
            clean["units"] = units[:40]
        now = db.utcnow()
        with self.p.engine.begin() as conn:
            for k, v in clean.items():
                payload = json.dumps(v, ensure_ascii=False)
                updated = conn.execute(
                    db.app_settings.update().where(db.app_settings.c.key == k).values(value_json=payload, updated_at=now, updated_by=actor.id)
                ).rowcount
                if not updated:
                    conn.execute(db.app_settings.insert().values(key=k, value_json=payload, updated_at=now, updated_by=actor.id))
            audit(conn, C.LOG_SISTEMA, "configuracoes_alteradas", actor, summary="Configurações administrativas alteradas",
                  campos=sorted(clean))
        with self._lock:
            self._cache_at = 0.0

    # ------------------------------------------------------------------ #
    # Logs
    # ------------------------------------------------------------------ #
    def logs(self, actor: User, *, categories: list[str] | None = None, q: str = "", limit: int = 1000,
             date_from: datetime | None = None, date_to: datetime | None = None,
             user_id: str | None = None) -> list[dict]:
        require_admin(actor)
        stmt = sa.select(db.audit_log).order_by(db.audit_log.c.id.desc()).limit(limit)
        if user_id:
            stmt = stmt.where(sa.or_(db.audit_log.c.actor_id == user_id, db.audit_log.c.target_id == user_id))
        if categories:
            stmt = stmt.where(db.audit_log.c.category.in_(categories))
        if date_from:
            stmt = stmt.where(db.audit_log.c.ts >= date_from)
        if date_to:
            stmt = stmt.where(db.audit_log.c.ts <= date_to)
        with self.p.engine.connect() as conn:
            rows = [dict(r._mapping) for r in conn.execute(stmt)]
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in f"{r['action']} {r['actor_login'] or ''} {r['summary']}".lower()]
        return rows

    # ------------------------------------------------------------------ #
    # Backup completo (dados + PDFs) para migração ou recuperação
    # ------------------------------------------------------------------ #
    def export_backup(self, actor: User, *, include_password_hashes: bool = True) -> bytes:
        require_admin(actor)
        buf = io.BytesIO()
        missing: list[str] = []
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            counts = {}
            keys: set[str] = set()
            with self.p.engine.connect() as conn:
                for table in BACKUP_TABLES:
                    rows = [dict(r._mapping) for r in conn.execute(sa.select(table))]
                    if table is db.users and not include_password_hashes:
                        for r in rows:
                            r["password_hash"] = "!redefinir"
                            r["must_change_password"] = True
                    counts[table.name] = len(rows)
                    zf.writestr(f"tabelas/{table.name}.json", json.dumps(rows, ensure_ascii=False, default=_json_default, indent=1))
                    if table is db.versions:
                        keys |= {r["pdf_key"] for r in rows if r["pdf_key"]}
                    if table is db.reviews:
                        keys |= {r["parecer_key"] for r in rows if r["parecer_key"]}
                    if table is db.exercise_figures:
                        keys |= {r["ref"] for r in rows if r["source"] == "arquivo"}
            for key in sorted(keys):
                try:
                    zf.writestr(f"arquivos/{key}", self.p.store.get(key))
                except StorageFailure:
                    missing.append(key)
            manifest = {
                "plataforma": "Circuitos Elétricos I — Exercícios Resolvidos",
                "schema_version": db.SCHEMA_VERSION,
                "gerado_em_utc": db.utcnow().isoformat(),
                "gerado_por": actor.login,
                "registros": counts,
                "arquivos": len(keys) - len(missing),
                "arquivos_ausentes": missing,
                "inclui_hash_de_senhas": include_password_hashes,
            }
            zf.writestr("manifesto.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        with self.p.engine.begin() as conn:
            audit(conn, C.LOG_SISTEMA, "backup_exportado", actor, summary=f"Backup completo exportado ({len(keys)} arquivos)",
                  arquivos_ausentes=len(missing))
        return buf.getvalue()

    # ------------------------------------------------------------------ #
    # Integridade das publicações
    # ------------------------------------------------------------------ #
    def integrity_check(self, actor: User, *, check_videos: bool = True) -> list[dict]:
        require_admin(actor)
        issues: list[dict] = []
        author = db.users.alias("author")
        with self.p.engine.connect() as conn:
            vrows = [
                dict(r._mapping)
                for r in conn.execute(
                    sa.select(db.versions, db.exercises.c.code, author.c.full_name.label("author_name"),
                              db.submissions.c.is_published, db.submissions.c.published_version_id)
                    .join(db.submissions, db.submissions.c.id == db.versions.c.submission_id)
                    .join(db.exercises, db.exercises.c.id == db.submissions.c.exercise_id)
                    .join(author, author.c.id == db.submissions.c.author_id)
                )
            ]
            rrows = [
                dict(r._mapping)
                for r in conn.execute(
                    sa.select(db.reviews.c.id, db.reviews.c.parecer_key, db.reviews.c.submission_id,
                              db.reviews.c.version_no, db.exercises.c.code, author.c.full_name.label("author_name"))
                    .join(db.submissions, db.submissions.c.id == db.reviews.c.submission_id)
                    .join(db.exercises, db.exercises.c.id == db.submissions.c.exercise_id)
                    .join(author, author.c.id == db.submissions.c.author_id)
                    .where(db.reviews.c.parecer_key.isnot(None))
                )
            ]
        alerts: dict[str, list[str]] = {}
        checked_keys: dict[str, bool] = {}

        def exists(key):
            if key not in checked_keys:
                try:
                    checked_keys[key] = self.p.store.exists(key)
                except StorageFailure:
                    checked_keys[key] = False
            return checked_keys[key]

        for v in vrows:
            if v["state"] == C.V_RASCUNHO and not v["pdf_key"]:
                continue
            published = bool(v["is_published"]) and v["published_version_id"] == v["id"]
            where = f"Exercício {v['code']} · {v['author_name']} · v{v['version_no']}"
            if v["pdf_key"] and not exists(v["pdf_key"]):
                issues.append({"tipo": "PDF ausente", "onde": where, "detalhe": "Arquivo não encontrado no armazenamento.",
                               "submission_id": v["submission_id"], "review_id": None, "publicada": published})
                if published:
                    alerts.setdefault(v["submission_id"], []).append("PDF indisponível")
            if published:
                try:
                    validate_falstad_url(v["falstad_url"] or "")
                except ValidationError as exc:
                    issues.append({"tipo": "Link Falstad", "onde": where, "detalhe": exc.message,
                                   "submission_id": v["submission_id"], "review_id": None, "publicada": True})
                    alerts.setdefault(v["submission_id"], []).append("Link do Falstad inválido")
                if check_videos and v["youtube_id"]:
                    chk = check_youtube_video(v["youtube_id"], api_key=self.p.settings.youtube_api_key, http_get=self.p.http_get)
                    if chk.status in (C.VIDEO_INEXISTENTE, C.VIDEO_RESTRITO):
                        issues.append({"tipo": "Vídeo", "onde": where, "detalhe": C.VIDEO_CHECK_LABELS[chk.status],
                                       "submission_id": v["submission_id"], "review_id": None, "publicada": True})
                        alerts.setdefault(v["submission_id"], []).append("Vídeo indisponível no YouTube")
                    elif chk.status == C.VIDEO_NAO_VERIFICADO:
                        issues.append({"tipo": "Vídeo (não verificado)", "onde": where, "detalhe": chk.detail,
                                       "submission_id": v["submission_id"], "review_id": None, "publicada": True})
        for r in rrows:
            if not exists(r["parecer_key"]):
                issues.append({"tipo": "Parecer ausente", "onde": f"Exercício {r['code']} · {r['author_name']} · v{r['version_no']}",
                               "detalhe": "PDF do parecer não encontrado; pode ser regenerado.",
                               "submission_id": r["submission_id"], "review_id": r["id"], "publicada": False})

        published_ids = {v["submission_id"] for v in vrows if v["is_published"]}
        with self.p.engine.begin() as conn:
            for sid in published_ids:
                text = "; ".join(sorted(set(alerts.get(sid, [])))) or None
                if not check_videos and text is None:
                    # Sem checagem de vídeo, preserva alertas de vídeo anteriores.
                    continue
                conn.execute(db.submissions.update().where(db.submissions.c.id == sid).values(resource_alert=text))
            audit(conn, C.LOG_SISTEMA, "integridade_verificada", actor,
                  summary=f"Verificação de integridade: {len(issues)} ocorrência(s)", videos=check_videos)
        return issues

    # ------------------------------------------------------------------ #
    # Diagnóstico (sem expor segredos)
    # ------------------------------------------------------------------ #
    def diagnostics(self, actor: User) -> list[tuple[str, str, bool]]:
        require_admin(actor)
        s = self.p.settings
        out = []
        try:
            with self.p.engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            out.append(("Banco de dados", f"{self.p.engine.dialect.name} conectado", True))
        except Exception as exc:
            out.append(("Banco de dados", f"Falha de conexão ({type(exc).__name__})", False))
        try:
            self.p.store.healthcheck()
            out.append(("Armazenamento de PDFs", f"{self.p.store.name} acessível", True))
        except Exception as exc:
            msg = exc.message if hasattr(exc, "message") else type(exc).__name__
            out.append(("Armazenamento de PDFs", msg, False))
        out.append(("Modo", "Demonstração (dados de teste)" if s.is_demo else "Produção", not s.is_demo))
        out.append(("Verificação de vídeos", "YouTube Data API (com duração)" if s.youtube_api_key else "oEmbed público (sem duração)", True))
        out.append(("Configuração inicial (bootstrap)", "token definido" if s.bootstrap_token else "desativada", True))
        return out
