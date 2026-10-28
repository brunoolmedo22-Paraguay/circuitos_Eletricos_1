"""Restaura um backup (ZIP gerado em Administração → Configurações → Backup).

Uso: configure os segredos do NOVO banco/armazenamento e execute

    python scripts/restaurar_backup.py caminho/backup_ce1_AAAAMMDD_HHMM.zip

O banco de destino precisa estar vazio (sem usuários).
"""

from __future__ import annotations

import sys
from pathlib import Path

from _comum import platform


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    from resolucoes.backup import restore_backup

    p = platform()
    report = restore_backup(Path(sys.argv[1]).read_bytes(), p)
    print("Backup restaurado.")
    for table, n in report["registros"].items():
        print(f"  {table}: {n}")
    print(f"  arquivos: {report['arquivos']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
