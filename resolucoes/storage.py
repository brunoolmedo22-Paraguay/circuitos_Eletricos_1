"""Armazenamento persistente de arquivos (PDFs das resoluções e pareceres).

Três implementações com a mesma interface, para que a plataforma possa trocar
de provedor sem reescrever funcionalidades:

* :class:`SupabaseFileStore` — Supabase Storage (bucket **privado**), usado em
  produção. Os arquivos ficam fora do GitHub e sobrevivem a reinícios e deploys.
* :class:`DatabaseFileStore` — guarda os bytes no próprio PostgreSQL. Útil em
  provedores que só oferecem banco (Neon etc.), ao custo de consumir a cota do
  banco.
* :class:`LocalFileStore` — disco local. **Somente** para desenvolvimento,
  testes ou servidor próprio com disco persistente.

As chaves dos arquivos são sempre geradas pela aplicação; nenhuma URL pública é
exposta. O acesso passa pelas verificações de permissão da camada de serviços.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import quote

import sqlalchemy as sa

from . import db
from .errors import StorageFailure

log = logging.getLogger(__name__)

_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-./]{0,280}$")


def _check_key(key: str) -> str:
    if not _KEY_RE.match(key) or ".." in key or key.startswith("/"):
        raise StorageFailure("Identificador de arquivo inválido.")
    return key


class FileStore(Protocol):
    name: str

    def put(self, key: str, data: bytes, content_type: str = "application/pdf") -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def healthcheck(self) -> None: ...


# --------------------------------------------------------------------------- #
class LocalFileStore:
    name = "local"

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / _check_key(key)

    def put(self, key, data, content_type="application/pdf"):
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(path)  # gravação atômica: nunca deixa arquivo pela metade

    def get(self, key):
        path = self._path(key)
        if not path.exists():
            raise StorageFailure("O arquivo solicitado não foi encontrado no armazenamento.")
        return path.read_bytes()

    def delete(self, key):
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key):
        return self._path(key).exists()

    def healthcheck(self):
        self.root.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
class DatabaseFileStore:
    name = "database"

    def __init__(self, engine: sa.Engine):
        self.engine = engine

    def put(self, key, data, content_type="application/pdf"):
        _check_key(key)
        try:
            with self.engine.begin() as conn:
                conn.execute(db.files.delete().where(db.files.c.key == key))
                conn.execute(
                    db.files.insert().values(
                        key=key, content=data, content_type=content_type, size=len(data), created_at=db.utcnow()
                    )
                )
        except sa.exc.SQLAlchemyError as exc:
            log.exception("Falha ao gravar arquivo no banco")
            raise StorageFailure() from exc

    def get(self, key):
        _check_key(key)
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(db.files.c.content).where(db.files.c.key == key)).first()
        if row is None:
            raise StorageFailure("O arquivo solicitado não foi encontrado no armazenamento.")
        return bytes(row[0])

    def delete(self, key):
        _check_key(key)
        with self.engine.begin() as conn:
            conn.execute(db.files.delete().where(db.files.c.key == key))

    def exists(self, key):
        _check_key(key)
        with self.engine.connect() as conn:
            return conn.execute(sa.select(db.files.c.key).where(db.files.c.key == key)).first() is not None

    def healthcheck(self):
        with self.engine.connect() as conn:
            conn.execute(sa.select(sa.func.count()).select_from(db.files))


# --------------------------------------------------------------------------- #
class SupabaseFileStore:
    """Cliente mínimo da API REST do Supabase Storage (sem SDK adicional).

    Aceita tanto a chave secreta nova (``sb_secret_…``), enviada apenas no
    cabeçalho ``apikey``, quanto a chave legada ``service_role`` (JWT), enviada
    também em ``Authorization``. A chave só existe no servidor; o navegador do
    usuário nunca a recebe.
    """

    name = "supabase"

    def __init__(self, url: str, key: str, bucket: str, *, session=None, timeout: float = 30.0):
        import requests

        self.base = url.rstrip("/") + "/storage/v1"
        self.bucket = bucket
        self.timeout = timeout
        self.http = session or requests.Session()
        headers = {"apikey": key}
        if not key.startswith(("sb_secret_", "sb_publishable_")):
            headers["Authorization"] = f"Bearer {key}"
        self.http.headers.update(headers)

    def _obj_url(self, key: str) -> str:
        return f"{self.base}/object/{self.bucket}/{quote(_check_key(key))}"

    def _request(self, method: str, url: str, **kw):
        try:
            return self.http.request(method, url, timeout=self.timeout, **kw)
        except Exception as exc:  # erros de rede
            log.warning("Supabase Storage indisponível: %s", type(exc).__name__)
            raise StorageFailure() from exc

    def put(self, key, data, content_type="application/pdf"):
        resp = self._request(
            "POST",
            self._obj_url(key),
            data=data,
            headers={"Content-Type": content_type, "x-upsert": "true", "cache-control": "3600"},
        )
        if resp.status_code not in (200, 201):
            log.warning("Upload Supabase falhou: HTTP %s %s", resp.status_code, resp.text[:200])
            raise StorageFailure("Não foi possível gravar o arquivo no armazenamento. Tente novamente.")

    def get(self, key):
        resp = self._request("GET", self._obj_url(key))
        if resp.status_code == 200:
            return resp.content
        if resp.status_code in (400, 404):
            raise StorageFailure("O arquivo solicitado não foi encontrado no armazenamento.")
        log.warning("Download Supabase falhou: HTTP %s", resp.status_code)
        raise StorageFailure()

    def delete(self, key):
        resp = self._request("DELETE", self._obj_url(key))
        if resp.status_code not in (200, 204, 400, 404):
            log.warning("Remoção Supabase falhou: HTTP %s", resp.status_code)

    def exists(self, key):
        resp = self._request("GET", self._obj_url(key), headers={"Range": "bytes=0-0"})
        if resp.status_code in (200, 206):
            return True
        if resp.status_code in (400, 404):
            return False
        raise StorageFailure()

    def ensure_bucket(self) -> bool:
        """Cria o bucket privado se ele não existir. Retorna True se criou."""
        resp = self._request("GET", f"{self.base}/bucket/{self.bucket}")
        if resp.status_code == 200:
            return False
        resp = self._request(
            "POST",
            f"{self.base}/bucket",
            json={"id": self.bucket, "name": self.bucket, "public": False, "allowed_mime_types": ["application/pdf"]},
        )
        if resp.status_code not in (200, 201):
            raise StorageFailure(f"Não foi possível criar o bucket '{self.bucket}' (HTTP {resp.status_code}).")
        return True

    def healthcheck(self):
        resp = self._request("GET", f"{self.base}/bucket/{self.bucket}")
        if resp.status_code != 200:
            raise StorageFailure(
                f"Bucket '{self.bucket}' inacessível (HTTP {resp.status_code}). Verifique a URL, a chave e o nome do bucket."
            )


def build_store(settings, engine: sa.Engine, *, http_session_factory: Callable | None = None) -> FileStore:
    backend = settings.storage_backend
    if backend == "supabase":
        session = http_session_factory() if http_session_factory else None
        return SupabaseFileStore(settings.supabase_url, settings.supabase_key, settings.storage_bucket, session=session)
    if backend == "database":
        return DatabaseFileStore(engine)
    return LocalFileStore(settings.local_storage_dir)
