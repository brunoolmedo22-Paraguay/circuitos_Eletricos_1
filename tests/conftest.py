"""Fixtures dos testes automatizados.

Por padrão os testes rodam em SQLite temporário. Para executá-los também contra
PostgreSQL (como em produção), defina ``CE1_TEST_PG_URL``, por exemplo:

    CE1_TEST_PG_URL=postgresql+psycopg2://usuario:senha@localhost:5432/ce1_test pytest
"""

from __future__ import annotations

import io
import os
import sys
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from resolucoes import constants as C  # noqa: E402
from resolucoes import db  # noqa: E402
from resolucoes.config import Settings  # noqa: E402
from resolucoes.services import Platform  # noqa: E402
from resolucoes.storage import DatabaseFileStore, LocalFileStore  # noqa: E402

BOOT = "token-de-configuracao-inicial-123"
FALSTAD = (
    "https://www.falstad.com/circuit/circuitjs.html?ctz=CQAgjCAMB0l3BWcMBMcUHYMGZIA4UA2ATmIxAUgoqoQFMBaMMAKAHcQUUAWTkPlHhCRceEQpQQ+8UuQiC2wmXKnTkMkEQpVqmgHJlTVaHQ0UA0F8hc7Q+u3EoQ8Uh7cJnYw91ssA"
)
YOUTUBE = "https://youtu.be/dQw4w9WgXcQ"


def make_pdf(text: str = "Resolução", pages: int = 1) -> bytes:
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(pages):
        c.drawString(72, 720, f"{text} — página {i + 1}")
        c.showPage()
    c.save()
    return buf.getvalue()


class FakeResp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeYouTube:
    """Simula o oEmbed do YouTube sem acesso à rede."""

    def __init__(self):
        self.status = {}  # video_id -> HTTP status
        self.calls = 0

    def __call__(self, url, params=None, timeout=None):
        self.calls += 1
        vid = (params or {}).get("url", "").split("v=")[-1]
        code = self.status.get(vid, 200)
        return FakeResp(code, {"title": f"Vídeo {vid}", "author_name": "Canal do Aluno"} if code == 200 else {})


def _pg_url():
    return os.environ.get("CE1_TEST_PG_URL")


BACKENDS = ["sqlite+database", "sqlite+local"] + (["postgres+database", "postgres+local"] if _pg_url() else [])


@pytest.fixture(params=BACKENDS)
def platform(request, tmp_path):
    kind, store_kind = request.param.split("+")
    if kind == "sqlite":
        url = f"sqlite:///{tmp_path / 'ce1.db'}"
    else:
        url = _pg_url()
        eng = db.get_engine(url)
        db.metadata.drop_all(eng)
    settings = Settings(
        database_url=url,
        storage_backend=store_kind,
        local_storage_dir=str(tmp_path / "arquivos"),
        bootstrap_token=BOOT,
        mode="demonstracao",
    )
    yt = FakeYouTube()
    p = Platform(settings, http_get=yt)
    p.fake_youtube = yt
    yield p
    if kind == "postgres":
        db.metadata.drop_all(p.engine)


@pytest.fixture
def actors(platform):
    """Dois administradores (monitor e professor) e dois alunos."""
    p = platform
    monitor = p.users.bootstrap_admin(BOOT, login="monitor", full_name="Monitor da Disciplina",
                                      email="monitor@unila.edu.br", password="Monitor2026")
    prof, _ = p.users.create(monitor, login="professor", full_name="Professora Responsável",
                             email="prof@unila.edu.br", role=C.ROLE_ADMIN, password="Professora2026")
    ana, _ = p.users.create(monitor, login="ana", full_name="Ana Souza", matricula="2024001",
                            email="ana@aluno.unila.edu.br", password="AnaSenha123")
    beto, _ = p.users.create(monitor, login="beto", full_name="Beto Lima", matricula="2024002",
                             email="beto@aluno.unila.edu.br", password="BetoSenha123")
    return {"monitor": monitor, "prof": prof, "ana": ana, "beto": beto}


@pytest.fixture
def exercise(platform, actors):
    return platform.exercises.create(
        actors["monitor"], code="2.04", title="Análise de Malhas",
        statement="Determine as correntes de malha $I_1$ e $I_2$ do circuito da figura.",
        unit="Unidade 2 — Métodos de Análise", topics="malhas, LKT, sistemas lineares",
    )


def row_version(p, sid):
    with p.engine.connect() as conn:
        return conn.execute(sa.select(db.submissions.c.row_version).where(db.submissions.c.id == sid)).scalar_one()


def fill_and_submit(p, student, exercise, *, yt=YOUTUBE, pdf=None, duration="6:30"):
    sid = p.submissions.start(student, exercise.id)
    p.submissions.save_draft(
        student, sid, expected_row_version=row_version(p, sid), youtube_url=yt, falstad_url=FALSTAD,
        duration_text=duration, pdf_bytes=pdf or make_pdf("v1"), pdf_name="minha_resolucao.pdf",
    )
    p.submissions.submit(student, sid, expected_row_version=row_version(p, sid), declaration=True)
    return sid


GOOD_CRITERIA = {k: {"rating": C.RATING_ATENDE, "comment": ""} for k, _ in C.CRITERIA}
ALL_REQ = {k: True for k, _ in C.REQUIREMENTS}


def uid() -> str:
    return uuid.uuid4().hex[:8]
