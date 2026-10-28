"""Teste E (persistência), validações, falhas de armazenamento, Supabase e backup."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import sqlalchemy as sa

from resolucoes import constants as C
from resolucoes import db
from resolucoes.backup import restore_backup
from resolucoes.config import Settings
from resolucoes.errors import StorageFailure, ValidationError
from resolucoes.services import Platform
from resolucoes.storage import LocalFileStore, SupabaseFileStore
from resolucoes.validators import (
    parse_duration_text,
    parse_youtube_id,
    validate_falstad_url,
    validate_pdf,
)

from conftest import ALL_REQ, FALSTAD, GOOD_CRITERIA, FakeYouTube, fill_and_submit, make_pdf, row_version


# --------------------------------------------------------------------------- #
# Validadores
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ?si=abc123",
        "youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/live/dQw4w9WgXcQ?feature=share",
        "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
    ],
)
def test_youtube_formatos_aceitos(url):
    assert parse_youtube_id(url) == "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        "", "https://vimeo.com/123", "https://www.youtube.com/@canal", "https://www.youtube.com/playlist?list=PL123",
        "https://www.youtube.com/watch?v=curto", "https://drive.google.com/file/d/abc",
    ],
)
def test_youtube_formatos_recusados(url):
    with pytest.raises(ValidationError):
        parse_youtube_id(url)


def test_falstad():
    assert validate_falstad_url("  " + FALSTAD + " ") == FALSTAD
    cct = "https://www.falstad.com/circuit/circuitjs.html?cct=$+1+0.000005+10+50+5+43%0Ar+1+2+3+4+0+1000"
    assert validate_falstad_url(cct) == cct
    for bad in (
        "https://www.falstad.com/circuit/circuitjs.html",
        "https://www.falstad.com/circuit/circuitjs.html?ctz=abc",
        "https://tinyurl.com/abc123",
        "https://example.com/circuitjs.html?ctz=" + "A" * 40,
        "falstad.com/circuit/circuitjs.html?ctz=" + "A" * 40,
    ):
        with pytest.raises(ValidationError):
            validate_falstad_url(bad)


def test_pdf_validacoes():
    ok = make_pdf(pages=3)
    assert validate_pdf(ok, max_mb=10).pages == 3
    with pytest.raises(ValidationError, match="não é um PDF"):
        validate_pdf(b"GIF89a....", max_mb=10)
    with pytest.raises(ValidationError, match="corrompido"):
        validate_pdf(b"%PDF-1.4\n" + b"\x00" * 300, max_mb=10)
    with pytest.raises(ValidationError, match="excede"):
        validate_pdf(ok + b"0" * (2 * 1024 * 1024), max_mb=1)
    from pypdf import PdfReader, PdfWriter
    import io

    w = PdfWriter()
    w.append(PdfReader(io.BytesIO(ok)))
    w.encrypt(user_password="segredo", owner_password="dono")
    enc = io.BytesIO()
    w.write(enc)
    with pytest.raises(ValidationError, match="protegido"):
        validate_pdf(enc.getvalue(), max_mb=10)


def test_duracao():
    assert parse_duration_text("7:45") == 465
    assert parse_duration_text("1:02:03") == 3723
    assert parse_duration_text("") is None
    for bad in ("7", "7:75", "0:00", "abc"):
        with pytest.raises(ValidationError):
            parse_duration_text(bad)


def test_configuracao_nao_persistente_e_recusada_em_producao():
    assert Settings().problems()  # nada configurado
    s = Settings(database_url="sqlite:///x.db", storage_backend="local", mode="producao")
    assert any("Streamlit Cloud" in pr for pr in s.problems())
    assert Settings(database_url="sqlite:///x.db", storage_backend="local", mode="demonstracao").ready
    assert Settings(database_url="postgresql://u:p@h/db", storage_backend="supabase").problems()
    assert Settings(database_url="postgresql://u:p@h/db", storage_backend="supabase",
                    supabase_url="https://x.supabase.co", supabase_key="k").ready


# --------------------------------------------------------------------------- #
# Persistência após reinício
# --------------------------------------------------------------------------- #
def test_dados_e_pdfs_sobrevivem_a_reinicio(platform, actors, exercise):
    p, monitor = platform, actors["monitor"]
    sid = fill_and_submit(p, actors["ana"], exercise)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    rid = p.reviews.return_for_correction(monitor, sid, expected_row_version=row_version(p, sid),
                                          requirements=ALL_REQ, criteria=GOOD_CRITERIA, problems="Ajustar unidades em V.")
    # "Reinício": nova instância, novo pool de conexões, novo cliente de armazenamento.
    p.engine.dispose()
    p2 = Platform(p.settings, http_get=FakeYouTube())
    det = p2.submissions.detail(actors["ana"], sid)
    assert det["submission"]["status"] == C.DEVOLVIDA
    assert p2.submissions.version_pdf(actors["ana"], det["current"]["id"])[0].startswith(b"%PDF")
    assert p2.reviews.parecer_pdf(actors["ana"], rid)[0].startswith(b"%PDF")
    assert p2.users.login("monitor", "Monitor2026")[0].is_admin


# --------------------------------------------------------------------------- #
# Falhas parciais não deixam estado inconsistente
# --------------------------------------------------------------------------- #
class FlakyStore(LocalFileStore):
    fail_put = False

    def put(self, key, data, content_type="application/pdf"):
        if self.fail_put:
            raise StorageFailure()
        return super().put(key, data, content_type)


def test_falha_de_armazenamento_nao_corrompe_entrega(tmp_path, actors, exercise, platform):
    store = FlakyStore(tmp_path / "flaky")
    p = Platform(platform.settings, engine=platform.engine, store=store, http_get=FakeYouTube())
    ana, monitor = actors["ana"], actors["monitor"]
    sid = p.submissions.start(ana, exercise.id)
    store.fail_put = True
    rv = row_version(p, sid)
    with pytest.raises(StorageFailure):
        p.submissions.save_draft(ana, sid, expected_row_version=rv, youtube_url="https://youtu.be/dQw4w9WgXcQ",
                                 pdf_bytes=make_pdf(), pdf_name="a.pdf")
    assert row_version(p, sid) == rv  # banco intacto
    assert p.submissions.detail(ana, sid)["current"]["youtube_id"] is None

    store.fail_put = False
    sid = fill_and_submit(p, actors["beto"], exercise)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    store.fail_put = True  # falha ao gravar o parecer
    with pytest.raises(StorageFailure):
        p.reviews.return_for_correction(monitor, sid, expected_row_version=row_version(p, sid),
                                        requirements=ALL_REQ, criteria=GOOD_CRITERIA, problems="Problema qualquer aqui.")
    det = p.submissions.detail(monitor, sid)
    assert det["submission"]["status"] == C.EM_ANALISE and det["reviews"] == []


def test_conflito_na_aprovacao_remove_parecer_orfao(platform, actors, exercise, tmp_path):
    store = LocalFileStore(tmp_path / "orf")
    p = Platform(platform.settings, engine=platform.engine, store=store, http_get=FakeYouTube())
    monitor = actors["monitor"]
    sid = fill_and_submit(p, actors["ana"], exercise)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    rv = row_version(p, sid)
    # Outro processo altera a submissão entre a leitura e a gravação
    with p.engine.begin() as conn:
        conn.execute(db.submissions.update().where(db.submissions.c.id == sid).values(row_version=rv + 5))
    from resolucoes.errors import ConflictError

    with pytest.raises(ConflictError):
        p.reviews.approve(monitor, sid, expected_row_version=rv, level=C.BOM, requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    assert not list((tmp_path / "orf" / "pareceres").rglob("*.pdf")) if (tmp_path / "orf" / "pareceres").exists() else True


def test_integridade_detecta_e_regenera_parecer(platform, actors, exercise):
    p, monitor = platform, actors["monitor"]
    sid = fill_and_submit(p, actors["ana"], exercise)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    rid = p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level=C.BOM,
                            requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    with p.engine.connect() as conn:
        key = conn.execute(sa.select(db.reviews.c.parecer_key).where(db.reviews.c.id == rid)).scalar_one()
    p.store.delete(key)
    p.fake_youtube.status["dQw4w9WgXcQ"] = 404  # vídeo removido após a aprovação
    issues = p.admin.integrity_check(monitor, check_videos=True)
    tipos = {i["tipo"] for i in issues}
    assert {"Parecer ausente", "Vídeo"} <= tipos
    assert "Vídeo indisponível" in p.catalog.published()[0]["resource_alert"]
    p.reviews.regenerate_parecer(monitor, rid)
    assert p.store.exists(key)


# --------------------------------------------------------------------------- #
# Backup e migração para outro provedor
# --------------------------------------------------------------------------- #
def test_backup_e_restauracao_em_outro_banco(platform, actors, exercise, tmp_path):
    p, monitor = platform, actors["monitor"]
    sid = fill_and_submit(p, actors["ana"], exercise)
    p.reviews.claim(monitor, sid, expected_row_version=row_version(p, sid))
    p.reviews.approve(monitor, sid, expected_row_version=row_version(p, sid), level=C.EXCELENTE,
                      requirements=ALL_REQ, criteria=GOOD_CRITERIA)
    blob = p.admin.export_backup(monitor)

    target = Platform(
        Settings(database_url=f"sqlite:///{tmp_path / 'destino.db'}", storage_backend="local",
                 local_storage_dir=str(tmp_path / "destino_arquivos"), mode="demonstracao"),
        http_get=FakeYouTube(),
    )
    report = restore_backup(blob, target)
    assert report["arquivos"] == 2  # PDF da resolução + parecer
    items = target.catalog.published()
    assert len(items) == 1 and items[0]["level"] == C.EXCELENTE
    assert target.submissions.version_pdf(None, items[0]["version_id"])[0].startswith(b"%PDF")
    user, _ = target.users.login("ana", "AnaSenha123")
    assert user.full_name == "Ana Souza"


# --------------------------------------------------------------------------- #
# Cliente do Supabase Storage contra um servidor HTTP simulado
# --------------------------------------------------------------------------- #
class _FakeSupabase(BaseHTTPRequestHandler):
    objects: dict = {}
    buckets: set = set()
    seen_headers: list = []

    def log_message(self, *a):
        pass

    def _send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        self.seen_headers.append(dict(self.headers))
        return self.headers.get("apikey") == "sb_secret_teste" and "Authorization" not in self.headers

    def do_GET(self):
        if not self._authorized():
            return self._send(401, b'{"error":"Invalid JWT"}')
        parts = self.path.split("/storage/v1/")[1]
        if parts.startswith("bucket/"):
            return self._send(200 if parts[7:] in self.buckets else 404, b"{}")
        key = parts[len("object/"):]
        if key in self.objects:
            return self._send(200, self.objects[key], "application/pdf")
        return self._send(400, b'{"error":"not_found"}')

    def do_POST(self):
        if not self._authorized():
            return self._send(401)
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        parts = self.path.split("/storage/v1/")[1]
        if parts == "bucket":
            self.buckets.add(json.loads(body)["id"])
            return self._send(200, b'{"name":"ok"}')
        self.objects[parts[len("object/"):]] = body
        return self._send(200, b'{"Key":"ok"}')

    def do_DELETE(self):
        key = self.path.split("/storage/v1/object/")[1]
        self.objects.pop(key, None)
        return self._send(200, b"[]")


def test_cliente_supabase_storage():
    server = HTTPServer(("127.0.0.1", 0), _FakeSupabase)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}"
        store = SupabaseFileStore(url, "sb_secret_teste", "resolucoes")
        assert store.ensure_bucket() is True
        store.healthcheck()
        key = "resolucoes/abc/v1/arquivo.pdf"
        store.put(key, b"%PDF-1.4 teste")
        assert store.exists(key)
        assert store.get(key) == b"%PDF-1.4 teste"
        store.delete(key)
        assert not store.exists(key)
        with pytest.raises(StorageFailure):
            store.get(key)
        bad = SupabaseFileStore(url, "chave-errada", "resolucoes")
        with pytest.raises(StorageFailure):
            bad.healthcheck()
    finally:
        server.shutdown()
