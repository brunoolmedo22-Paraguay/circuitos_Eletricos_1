"""Utilitários dos scripts de linha de comando.

Os scripts leem a configuração de ``.streamlit/secrets.toml`` (se existir) ou
das variáveis de ambiente ``CE1_*``. Nunca grave segredos neste repositório.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_MAP = {
    ("database", "url"): "CE1_DATABASE_URL",
    ("storage", "backend"): "CE1_STORAGE_BACKEND",
    ("storage", "supabase_url"): "CE1_SUPABASE_URL",
    ("storage", "supabase_key"): "CE1_SUPABASE_KEY",
    ("storage", "bucket"): "CE1_STORAGE_BUCKET",
    ("storage", "local_dir"): "CE1_LOCAL_STORAGE_DIR",
    ("auth", "bootstrap_token"): "CE1_BOOTSTRAP_TOKEN",
    ("youtube", "api_key"): "CE1_YOUTUBE_API_KEY",
    ("app", "mode"): "CE1_MODE",
    ("app", "allow_local_persistence"): "CE1_ALLOW_LOCAL_PERSISTENCE",
}


def load_env_from_secrets(path: str | None = None) -> None:
    secrets = Path(path) if path else ROOT / ".streamlit" / "secrets.toml"
    if not secrets.exists():
        return
    try:
        import tomllib
    except ImportError:  # Python < 3.11
        import tomli as tomllib  # type: ignore
    data = tomllib.loads(secrets.read_text(encoding="utf-8"))
    for (sec, key), env in _MAP.items():
        val = (data.get(sec) or {}).get(key)
        if val not in (None, "") and not os.environ.get(env):
            os.environ[env] = str(val)


def platform(**overrides):
    load_env_from_secrets(os.environ.get("CE1_SECRETS_FILE"))
    from resolucoes.config import load_settings
    from resolucoes.services import Platform

    settings = load_settings(overrides or None)
    problems = settings.problems()
    if problems:
        print("Configuração incompleta:\n - " + "\n - ".join(problems))
        sys.exit(2)
    return Platform(settings)
