"""Consulta leve ao banco para evitar a pausa por inatividade do plano gratuito do Supabase.

Executado semanalmente pelo workflow .github/workflows/manter-supabase-ativo.yml
(usa o segredo CE1_DATABASE_URL do repositório; não grava nada no Git).
"""

from __future__ import annotations

import os
import sys

import sqlalchemy as sa


def main() -> int:
    url = os.environ.get("CE1_DATABASE_URL")
    if not url:
        print("CE1_DATABASE_URL não definido; nada a fazer.")
        return 0
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    eng = sa.create_engine(url, connect_args={"connect_timeout": 20})
    with eng.connect() as conn:
        n = conn.execute(sa.text("SELECT count(*) FROM ce1_users")).scalar()
    print(f"Banco ativo ({n} usuários).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
