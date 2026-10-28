"""Cria um administrador ou redefine a senha de qualquer conta (recuperação).

Uso (na pasta do projeto, com os segredos configurados):

    python scripts/criar_admin.py                       # cria administrador (pergunta os dados)
    python scripts/criar_admin.py --redefinir LOGIN     # gera senha provisória e reativa a conta

Quem executa este script precisa da URL do banco de dados; por isso ele não
exige o token de configuração inicial. Toda ação fica registrada no log.
"""

from __future__ import annotations

import argparse
import getpass
import sys
import uuid

from _comum import platform


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--redefinir", metavar="LOGIN", help="gera senha provisória para LOGIN e reativa a conta")
    args = ap.parse_args()

    import sqlalchemy as sa

    from resolucoes import constants as C
    from resolucoes import db, security
    from resolucoes.errors import AppError
    from resolucoes.services.common import audit, row_to_user
    from resolucoes.services.users import normalize_login

    p = platform()
    if args.redefinir:
        login = normalize_login(args.redefinir)
        temp = security.generate_temp_password()
        with p.engine.begin() as conn:
            row = conn.execute(sa.select(db.users).where(db.users.c.login == login)).first()
            if row is None:
                print(f"Login '{login}' não encontrado.")
                return 1
            conn.execute(db.users.update().where(db.users.c.login == login).values(
                password_hash=security.hash_password(temp), must_change_password=True, active=True,
                failed_attempts=0, locked_until=None, updated_at=db.utcnow()))
            conn.execute(db.sessions.update().where(db.sessions.c.user_id == row.id).values(revoked=True))
            audit(conn, C.LOG_USUARIO, "senha_redefinida_cli", None, actor_login="linha-de-comando",
                  target_type="usuario", target_id=row.id, summary=f"Senha redefinida via script para {login}")
        print(f"Senha provisória de '{login}': {temp}\nEla deverá ser trocada no próximo acesso.")
        return 0

    print("== Novo administrador ==")
    name = input("Nome completo: ").strip()
    login = input("Login: ").strip()
    email = input("E-mail (opcional): ").strip()
    pwd = getpass.getpass("Senha (mín. 8, letras e números): ")
    if pwd != getpass.getpass("Confirme a senha: "):
        print("As senhas não coincidem.")
        return 1
    try:
        security.validate_password_strength(pwd, login=login)
        with p.engine.begin() as conn:
            data = p.users._validate_identity(conn, login=login, full_name=name, email=email, matricula=None, phone=None)
            user = p.users._insert(conn, data=data, role=C.ROLE_ADMIN, password=pwd, must_change=False, created_by=None)
            audit(conn, C.LOG_USUARIO, "admin_criado_cli", None, actor_login="linha-de-comando", target_type="usuario",
                  target_id=user.id, summary=f"Administrador criado via script: {user.login}")
    except AppError as exc:
        print("Erro:", exc.message)
        return 1
    print(f"Administrador '{user.login}' criado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
