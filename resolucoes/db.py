"""Esquema relacional e conexão com o banco de dados.

O esquema usa SQLAlchemy Core com tipos portáveis, de modo que o mesmo código
funciona em PostgreSQL (produção: Supabase, Neon, servidor da universidade…) e
em SQLite (desenvolvimento e testes). Migrar de provedor exige apenas trocar a
URL de conexão e restaurar um backup (ver ``scripts/restaurar_backup.py``).

Relação central preservada:
    exercício proposto → aluno → submissão → versões → avaliações → publicação
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

import sqlalchemy as sa

SCHEMA_VERSION = 1

metadata = sa.MetaData()


def utcnow() -> datetime:
    """Instante atual em UTC, sem tzinfo (armazenamento uniforme em qualquer banco)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


users = sa.Table(
    "ce1_users",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("login", sa.String(120), nullable=False, unique=True),
    sa.Column("full_name", sa.String(200), nullable=False),
    sa.Column("public_name", sa.String(200), nullable=True),
    sa.Column("email", sa.String(200), nullable=True),
    sa.Column("matricula", sa.String(40), nullable=True),
    sa.Column("phone", sa.String(40), nullable=True),
    sa.Column("role", sa.String(20), nullable=False),
    sa.Column("active", sa.Boolean, nullable=False, default=True),
    sa.Column("password_hash", sa.String(300), nullable=False),
    sa.Column("must_change_password", sa.Boolean, nullable=False, default=False),
    sa.Column("failed_attempts", sa.Integer, nullable=False, default=0),
    sa.Column("locked_until", sa.DateTime, nullable=True),
    sa.Column("created_at", sa.DateTime, nullable=False),
    sa.Column("updated_at", sa.DateTime, nullable=False),
    sa.Column("last_login_at", sa.DateTime, nullable=True),
    sa.Column("created_by", sa.String(36), nullable=True),
)
sa.Index("ix_ce1_users_matricula", users.c.matricula)
sa.Index("ix_ce1_users_email", users.c.email)

sessions = sa.Table(
    "ce1_sessions",
    metadata,
    sa.Column("token_hash", sa.String(64), primary_key=True),
    sa.Column("user_id", sa.String(36), sa.ForeignKey("ce1_users.id"), nullable=False),
    sa.Column("created_at", sa.DateTime, nullable=False),
    sa.Column("expires_at", sa.DateTime, nullable=False),
    sa.Column("last_seen_at", sa.DateTime, nullable=False),
    sa.Column("revoked", sa.Boolean, nullable=False, default=False),
)
sa.Index("ix_ce1_sessions_user", sessions.c.user_id)

exercises = sa.Table(
    "ce1_exercises",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("code", sa.String(20), nullable=False, unique=True),
    sa.Column("title", sa.String(200), nullable=False),
    sa.Column("statement", sa.Text, nullable=False),
    sa.Column("unit", sa.String(160), nullable=False, default=""),
    sa.Column("topics", sa.String(500), nullable=False, default=""),
    sa.Column("description", sa.Text, nullable=False, default=""),
    sa.Column("support_material", sa.Text, nullable=False, default=""),
    sa.Column("active", sa.Boolean, nullable=False, default=True),
    sa.Column("sort_key", sa.String(40), nullable=False, default=""),
    sa.Column("created_at", sa.DateTime, nullable=False),
    sa.Column("updated_at", sa.DateTime, nullable=False),
    sa.Column("created_by", sa.String(36), nullable=True),
    sa.Column("updated_by", sa.String(36), nullable=True),
)

submissions = sa.Table(
    "ce1_submissions",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("exercise_id", sa.String(36), sa.ForeignKey("ce1_exercises.id"), nullable=False),
    sa.Column("author_id", sa.String(36), sa.ForeignKey("ce1_users.id"), nullable=False),
    sa.Column("coauthors", sa.String(400), nullable=False, default=""),
    sa.Column("status", sa.String(20), nullable=False),
    sa.Column("current_version_no", sa.Integer, nullable=False, default=1),
    sa.Column("reviewer_id", sa.String(36), nullable=True),
    sa.Column("review_started_at", sa.DateTime, nullable=True),
    sa.Column("is_published", sa.Boolean, nullable=False, default=False),
    sa.Column("published_version_id", sa.String(36), nullable=True),
    sa.Column("published_review_id", sa.String(36), nullable=True),
    sa.Column("published_level", sa.String(20), nullable=True),
    sa.Column("published_at", sa.DateTime, nullable=True),
    sa.Column("first_approved_at", sa.DateTime, nullable=True),
    sa.Column("retired_reason", sa.Text, nullable=True),
    sa.Column("resource_alert", sa.Text, nullable=True),
    sa.Column("row_version", sa.Integer, nullable=False, default=1),
    sa.Column("created_at", sa.DateTime, nullable=False),
    sa.Column("updated_at", sa.DateTime, nullable=False),
    sa.Column("first_submitted_at", sa.DateTime, nullable=True),
    sa.Column("last_submitted_at", sa.DateTime, nullable=True),
    sa.UniqueConstraint("exercise_id", "author_id", name="uq_ce1_submission_exercise_author"),
)
sa.Index("ix_ce1_submissions_status", submissions.c.status)
sa.Index("ix_ce1_submissions_published", submissions.c.is_published)

versions = sa.Table(
    "ce1_versions",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("submission_id", sa.String(36), sa.ForeignKey("ce1_submissions.id"), nullable=False),
    sa.Column("version_no", sa.Integer, nullable=False),
    sa.Column("state", sa.String(20), nullable=False),
    sa.Column("youtube_url", sa.Text, nullable=True),
    sa.Column("youtube_id", sa.String(20), nullable=True),
    sa.Column("youtube_title", sa.String(300), nullable=True),
    sa.Column("youtube_channel", sa.String(200), nullable=True),
    sa.Column("video_check", sa.String(30), nullable=True),
    sa.Column("video_checked_at", sa.DateTime, nullable=True),
    sa.Column("video_duration_s", sa.Integer, nullable=True),
    sa.Column("video_duration_source", sa.String(20), nullable=True),  # api | declarada | verificada
    sa.Column("falstad_url", sa.Text, nullable=True),
    sa.Column("pdf_key", sa.String(300), nullable=True),
    sa.Column("pdf_filename", sa.String(200), nullable=True),
    sa.Column("pdf_size", sa.Integer, nullable=True),
    sa.Column("pdf_pages", sa.Integer, nullable=True),
    sa.Column("pdf_sha256", sa.String(64), nullable=True),
    sa.Column("student_notes", sa.Text, nullable=False, default=""),
    sa.Column("created_at", sa.DateTime, nullable=False),
    sa.Column("updated_at", sa.DateTime, nullable=False),
    sa.Column("submitted_at", sa.DateTime, nullable=True),
    sa.UniqueConstraint("submission_id", "version_no", name="uq_ce1_version_no"),
)

reviews = sa.Table(
    "ce1_reviews",
    metadata,
    sa.Column("id", sa.String(36), primary_key=True),
    sa.Column("submission_id", sa.String(36), sa.ForeignKey("ce1_submissions.id"), nullable=False),
    sa.Column("version_id", sa.String(36), sa.ForeignKey("ce1_versions.id"), nullable=False),
    sa.Column("version_no", sa.Integer, nullable=False),
    sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("ce1_users.id"), nullable=False),
    sa.Column("kind", sa.String(20), nullable=False),
    sa.Column("decision", sa.String(20), nullable=False),
    sa.Column("level", sa.String(20), nullable=True),
    sa.Column("previous_level", sa.String(20), nullable=True),
    sa.Column("requirements_json", sa.Text, nullable=False, default="{}"),
    sa.Column("criteria_json", sa.Text, nullable=False, default="{}"),
    sa.Column("problems", sa.Text, nullable=False, default=""),
    sa.Column("observations", sa.Text, nullable=False, default=""),
    sa.Column("recommendations", sa.Text, nullable=False, default=""),
    sa.Column("resubmit_instructions", sa.Text, nullable=False, default=""),
    sa.Column("parecer_key", sa.String(300), nullable=True),
    sa.Column("created_at", sa.DateTime, nullable=False),
)
sa.Index("ix_ce1_reviews_submission", reviews.c.submission_id)

audit_log = sa.Table(
    "ce1_audit_log",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("ts", sa.DateTime, nullable=False),
    sa.Column("category", sa.String(20), nullable=False),
    sa.Column("action", sa.String(60), nullable=False),
    sa.Column("actor_id", sa.String(36), nullable=True),
    sa.Column("actor_login", sa.String(120), nullable=True),
    sa.Column("target_type", sa.String(30), nullable=True),
    sa.Column("target_id", sa.String(36), nullable=True),
    sa.Column("summary", sa.String(500), nullable=False, default=""),
    sa.Column("details_json", sa.Text, nullable=False, default="{}"),
)
sa.Index("ix_ce1_audit_category_ts", audit_log.c.category, audit_log.c.ts)

app_settings = sa.Table(
    "ce1_settings",
    metadata,
    sa.Column("key", sa.String(80), primary_key=True),
    sa.Column("value_json", sa.Text, nullable=False),
    sa.Column("updated_at", sa.DateTime, nullable=False),
    sa.Column("updated_by", sa.String(36), nullable=True),
)

# Usada apenas quando [storage] backend = "database" (PDFs guardados no próprio banco).
files = sa.Table(
    "ce1_files",
    metadata,
    sa.Column("key", sa.String(300), primary_key=True),
    sa.Column("content", sa.LargeBinary, nullable=False),
    sa.Column("content_type", sa.String(80), nullable=False),
    sa.Column("size", sa.Integer, nullable=False),
    sa.Column("created_at", sa.DateTime, nullable=False),
)

ALL_TABLES = [users, sessions, exercises, submissions, versions, reviews, audit_log, app_settings, files]

_engines: dict[str, sa.Engine] = {}
_lock = threading.Lock()


def _make_engine(url: str) -> sa.Engine:
    if url.startswith("sqlite"):
        engine = sa.create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})

        @sa.event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

        return engine
    # PostgreSQL (Supabase via Session Pooler). Poucas conexões: o pooler do
    # plano gratuito tem limite de clientes simultâneos.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return sa.create_engine(
        url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        pool_recycle=300,
        connect_args={"connect_timeout": 10},
    )


def get_engine(url: str) -> sa.Engine:
    with _lock:
        if url not in _engines:
            _engines[url] = _make_engine(url)
        return _engines[url]


def init_schema(engine: sa.Engine) -> None:
    """Cria as tabelas ausentes (operação idempotente e não destrutiva)."""
    metadata.create_all(engine, checkfirst=True)
    if engine.dialect.name == "postgresql":
        # Defesa em profundidade no Supabase: a API REST automática (PostgREST)
        # expõe o schema "public". Com RLS ativo e sem políticas, as chaves
        # anon/publishable não leem nada; a conexão da aplicação (dona das
        # tabelas) não é afetada.
        with engine.begin() as conn:
            for table in ALL_TABLES:
                conn.execute(sa.text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY'))
    with engine.begin() as conn:
        row = conn.execute(sa.select(app_settings.c.key).where(app_settings.c.key == "_schema_version")).first()
        if row is None:
            try:
                with conn.begin_nested():
                    conn.execute(
                        app_settings.insert().values(
                            key="_schema_version", value_json=str(SCHEMA_VERSION), updated_at=utcnow(), updated_by=None
                        )
                    )
            except sa.exc.IntegrityError:  # outra instância inicializou ao mesmo tempo
                pass
