"""Leitura da configuração do módulo Exercícios Resolvidos.

Fontes, em ordem de prioridade:

1. ``st.secrets`` (``.streamlit/secrets.toml`` localmente ou o painel *Secrets*
   do Streamlit Community Cloud);
2. variáveis de ambiente ``CE1_*`` (usadas pelos scripts de linha de comando,
   pelos testes e por servidores próprios).

Nenhum segredo real é versionado no repositório. O arquivo
``.streamlit/secrets.toml.example`` documenta todas as chaves.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

MODE_PRODUCAO = "producao"
MODE_DEMO = "demonstracao"


@dataclass(frozen=True)
class Settings:
    database_url: str | None = None
    storage_backend: str = "supabase"          # supabase | database | local
    supabase_url: str | None = None
    supabase_key: str | None = None
    storage_bucket: str = "resolucoes"
    local_storage_dir: str = str(ROOT_DIR / ".dados_locais" / "arquivos")
    bootstrap_token: str | None = None
    session_hours: int = 12
    youtube_api_key: str | None = None
    mode: str = MODE_PRODUCAO
    allow_local_persistence: bool = False
    check_video_online: bool = True
    seed_content: bool = True               # importa os pacotes de exercícios na inicialização
    extra: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    @property
    def uses_sqlite(self) -> bool:
        return bool(self.database_url) and self.database_url.startswith("sqlite")

    @property
    def is_demo(self) -> bool:
        return self.mode == MODE_DEMO

    def problems(self) -> list[str]:
        """Lista problemas que impedem o funcionamento seguro.

        Uma configuração que descartaria dados ao reiniciar (SQLite ou disco
        local em produção) é tratada como erro, nunca como aviso.
        """
        issues: list[str] = []
        if not self.database_url:
            issues.append("Banco de dados não configurado (chave [database] url).")
        if self.storage_backend not in {"supabase", "database", "local"}:
            issues.append("Valor inválido em [storage] backend (use supabase, database ou local).")
        if self.storage_backend == "supabase" and not (self.supabase_url and self.supabase_key):
            issues.append("Armazenamento Supabase selecionado, mas faltam supabase_url e/ou supabase_key.")
        ephemeral = self.uses_sqlite or self.storage_backend == "local"
        if ephemeral and not (self.is_demo or self.allow_local_persistence):
            issues.append(
                "Configuração local (SQLite ou disco do servidor) em modo produção. "
                "No Streamlit Cloud esses dados desaparecem ao reiniciar. Configure um "
                "banco PostgreSQL e o armazenamento Supabase, ou ative o modo demonstração."
            )
        return issues

    @property
    def ready(self) -> bool:
        return not self.problems()


def _secrets_dict() -> dict:
    try:
        import streamlit as st

        try:
            return {k: (dict(v) if hasattr(v, "keys") else v) for k, v in st.secrets.items()}
        except Exception:
            return {}
    except Exception:  # pragma: no cover - streamlit ausente
        return {}


def _get(sec: dict, section: str, key: str, env: str, default=None):
    value = None
    block = sec.get(section)
    if isinstance(block, dict):
        value = block.get(key)
    if value in (None, ""):
        value = os.environ.get(env)
    if value in (None, ""):
        return default
    return value


def _as_bool(value, default=False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "sim", "yes", "on"}


def load_settings(overrides: dict | None = None) -> Settings:
    sec = _secrets_dict()
    data = dict(
        database_url=_get(sec, "database", "url", "CE1_DATABASE_URL"),
        storage_backend=str(_get(sec, "storage", "backend", "CE1_STORAGE_BACKEND", "supabase")).lower(),
        supabase_url=_get(sec, "storage", "supabase_url", "CE1_SUPABASE_URL"),
        supabase_key=_get(sec, "storage", "supabase_key", "CE1_SUPABASE_KEY"),
        storage_bucket=_get(sec, "storage", "bucket", "CE1_STORAGE_BUCKET", "resolucoes"),
        local_storage_dir=_get(
            sec, "storage", "local_dir", "CE1_LOCAL_STORAGE_DIR", str(ROOT_DIR / ".dados_locais" / "arquivos")
        ),
        bootstrap_token=_get(sec, "auth", "bootstrap_token", "CE1_BOOTSTRAP_TOKEN"),
        session_hours=int(_get(sec, "auth", "session_hours", "CE1_SESSION_HOURS", 12)),
        youtube_api_key=_get(sec, "youtube", "api_key", "CE1_YOUTUBE_API_KEY"),
        mode=str(_get(sec, "app", "mode", "CE1_MODE", MODE_PRODUCAO)).lower(),
        allow_local_persistence=_as_bool(
            _get(sec, "app", "allow_local_persistence", "CE1_ALLOW_LOCAL_PERSISTENCE"), False
        ),
        check_video_online=_as_bool(_get(sec, "youtube", "check_online", "CE1_CHECK_VIDEO_ONLINE"), True),
        seed_content=_as_bool(_get(sec, "app", "import_packs", "CE1_IMPORT_PACKS"), True),
    )
    if overrides:
        data.update(overrides)
    return Settings(**data)
