"""Restauração de backups gerados em Administração → Configurações → Backup.

Permite migrar todos os dados (usuários, exercícios, submissões, versões,
avaliações, logs e PDFs) para outro banco/armazenamento sem reconstruir nada.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime

import sqlalchemy as sa

from . import db
from .services.admin import BACKUP_TABLES


def _parse_dt(table: sa.Table, row: dict) -> dict:
    out = {}
    for col in table.columns:
        if col.name not in row:
            continue
        val = row[col.name]
        if isinstance(col.type, sa.DateTime) and isinstance(val, str):
            val = datetime.fromisoformat(val)
        out[col.name] = val
    return out


def restore_backup(zip_bytes: bytes, platform, *, allow_non_empty: bool = False) -> dict:
    """Restaura o backup em ``platform`` (banco + armazenamento de destino).

    Por segurança, o destino precisa estar vazio (sem usuários), a menos que
    ``allow_non_empty`` seja explicitamente informado.
    """
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    manifest = json.loads(zf.read("manifesto.json"))
    with platform.engine.connect() as conn:
        existing = conn.execute(sa.select(sa.func.count()).select_from(db.users)).scalar_one()
    if existing and not allow_non_empty:
        raise RuntimeError("O banco de destino já possui usuários. Restaure em um banco vazio.")

    # Arquivos primeiro: se algo falhar, o banco ainda não foi tocado.
    names = [n for n in zf.namelist() if n.startswith("arquivos/") and not n.endswith("/")]
    for name in names:
        platform.store.put(name[len("arquivos/"):], zf.read(name))

    counts = {}
    with platform.engine.begin() as conn:
        for table in BACKUP_TABLES:
            rows = json.loads(zf.read(f"tabelas/{table.name}.json"))
            if table is db.app_settings:
                conn.execute(table.delete())
            prepared = [_parse_dt(table, r) for r in rows]
            if prepared:
                conn.execute(table.insert(), prepared)
            counts[table.name] = len(prepared)
        if platform.engine.dialect.name == "postgresql":
            conn.execute(sa.text(
                "SELECT setval(pg_get_serial_sequence('ce1_audit_log','id'), COALESCE((SELECT MAX(id) FROM ce1_audit_log), 1))"
            ))
    platform.admin._cache_at = 0.0
    return {"manifesto": manifest, "registros": counts, "arquivos": len(names)}
