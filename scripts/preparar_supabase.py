"""Prepara um projeto Supabase novo: cria as tabelas e o bucket privado de PDFs.

    python scripts/preparar_supabase.py

Seguro para executar mais de uma vez (não apaga nada).
"""

from __future__ import annotations

import sys

from _comum import platform


def main() -> int:
    p = platform()
    print(f"Tabelas verificadas no banco ({p.engine.dialect.name}).")
    if p.store.name == "supabase":
        created = p.store.ensure_bucket()
        print("Bucket privado criado." if created else "Bucket já existia.")
    p.store.healthcheck()
    print("Armazenamento acessível. Próximo passo: configuração inicial do primeiro administrador.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
