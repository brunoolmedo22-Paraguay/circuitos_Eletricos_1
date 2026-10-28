"""Usuários, autenticação, sessões e perfis."""

from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import timedelta

import sqlalchemy as sa

from .. import constants as C
from .. import db, security
from ..errors import AuthError, ConflictError, NotFound, PermissionDenied, ValidationError
from .common import EMAIL_RE, User, audit, clean_text, require_admin, require_user, row_to_user

MAX_FAILED = 5
LOCK_MINUTES = 15
IDLE_HOURS = 4
_LOGIN_RE = re.compile(r"^[a-z0-9._@\-]{3,120}$")


def normalize_login(value: str) -> str:
    return (value or "").strip().lower()


class UserService:
    def __init__(self, platform):
        self.p = platform

    # ------------------------------------------------------------------ #
    # Consultas
    # ------------------------------------------------------------------ #
    def _get(self, conn, user_id: str) -> User:
        row = conn.execute(sa.select(db.users).where(db.users.c.id == user_id)).first()
        if row is None:
            raise NotFound("Usuário não encontrado.")
        return row_to_user(row)

    def get(self, actor: User, user_id: str) -> User:
        require_user(actor)
        if not actor.is_admin and actor.id != user_id:
            raise PermissionDenied()
        with self.p.engine.connect() as conn:
            return self._get(conn, user_id)

    def list(self, actor: User, *, q: str = "", role: str | None = None, active: bool | None = None) -> list[User]:
        require_admin(actor)
        stmt = sa.select(db.users).order_by(db.users.c.full_name)
        if role:
            stmt = stmt.where(db.users.c.role == role)
        if active is not None:
            stmt = stmt.where(db.users.c.active == active)
        with self.p.engine.connect() as conn:
            items = [row_to_user(r) for r in conn.execute(stmt)]
        if q:
            ql = q.strip().lower()
            items = [
                u for u in items
                if ql in " ".join(filter(None, [u.full_name, u.login, u.email, u.matricula])).lower()
            ]
        return items

    def admin_count(self, conn=None) -> int:
        stmt = sa.select(sa.func.count()).select_from(db.users).where(
            db.users.c.role == C.ROLE_ADMIN, db.users.c.active.is_(True)
        )
        if conn is not None:
            return conn.execute(stmt).scalar_one()
        with self.p.engine.connect() as c:
            return c.execute(stmt).scalar_one()

    # ------------------------------------------------------------------ #
    # Validação
    # ------------------------------------------------------------------ #
    def _validate_identity(self, conn, *, login, full_name, email, matricula, phone, exclude_id=None) -> dict:
        login = normalize_login(login)
        if not _LOGIN_RE.match(login):
            raise ValidationError(
                "Login inválido. Use de 3 a 120 caracteres: letras minúsculas, números, ponto, hífen, sublinhado ou @.",
                field="login",
            )
        full_name = clean_text(full_name, max_len=200, field="nome", label="Nome completo", required=True)
        if len(full_name) < 3:
            raise ValidationError("Informe o nome completo.", field="nome")
        email = (email or "").strip().lower() or None
        if email and not EMAIL_RE.match(email):
            raise ValidationError("E-mail inválido.", field="email")
        matricula = (matricula or "").strip() or None
        if matricula and not re.fullmatch(r"[A-Za-z0-9.\-/]{2,40}", matricula):
            raise ValidationError("Matrícula inválida.", field="matricula")
        phone = re.sub(r"[^\d+]", "", phone or "") or None
        if phone and not re.fullmatch(r"\+?\d{10,15}", phone):
            raise ValidationError("Telefone inválido. Informe DDI + DDD + número, por exemplo +5545999998888.", field="telefone")

        def taken(col, value):
            if not value:
                return False
            stmt = sa.select(db.users.c.id).where(sa.func.lower(col) == value.lower())
            if exclude_id:
                stmt = stmt.where(db.users.c.id != exclude_id)
            return conn.execute(stmt).first() is not None

        if taken(db.users.c.login, login):
            raise ValidationError("Já existe um usuário com este login.", field="login")
        if taken(db.users.c.email, email):
            raise ValidationError("Já existe um usuário com este e-mail.", field="email")
        if taken(db.users.c.matricula, matricula):
            raise ValidationError("Já existe um usuário com esta matrícula.", field="matricula")
        return dict(login=login, full_name=full_name, email=email, matricula=matricula, phone=phone)

    # ------------------------------------------------------------------ #
    # Criação
    # ------------------------------------------------------------------ #
    def _insert(self, conn, *, data: dict, role: str, password: str, must_change: bool, created_by: str | None) -> User:
        now = db.utcnow()
        uid = str(uuid.uuid4())
        conn.execute(
            db.users.insert().values(
                id=uid,
                login=data["login"],
                full_name=data["full_name"],
                public_name=data.get("public_name"),
                email=data["email"],
                matricula=data["matricula"],
                phone=data["phone"],
                role=role,
                active=True,
                password_hash=security.hash_password(password),
                must_change_password=must_change,
                failed_attempts=0,
                locked_until=None,
                created_at=now,
                updated_at=now,
                last_login_at=None,
                created_by=created_by,
            )
        )
        return self._get(conn, uid)

    def bootstrap_needed(self) -> bool:
        return self.admin_count() == 0

    def bootstrap_admin(self, token: str, *, login, full_name, email, password) -> User:
        """Cria o primeiro administrador. Exige o token secreto configurado no servidor."""
        expected = self.p.settings.bootstrap_token
        if not expected or len(expected) < 16:
            raise PermissionDenied(
                "Configuração inicial desativada: defina [auth] bootstrap_token (mínimo 16 caracteres) nos segredos."
            )
        if not security.constant_time_equals(token or "", expected):
            with self.p.engine.begin() as conn:
                audit(conn, C.LOG_USUARIO, "bootstrap_negado", None, actor_login=normalize_login(login),
                      summary="Tentativa de configuração inicial com token inválido")
            raise PermissionDenied("Token de configuração inválido.")
        with self.p.engine.begin() as conn:
            if self.admin_count(conn) > 0:
                raise ConflictError("A configuração inicial já foi concluída. Peça acesso a um administrador.")
            data = self._validate_identity(conn, login=login, full_name=full_name, email=email, matricula=None, phone=None)
            security.validate_password_strength(password, login=data["login"])
            user = self._insert(conn, data=data, role=C.ROLE_ADMIN, password=password, must_change=False, created_by=None)
            audit(conn, C.LOG_USUARIO, "admin_inicial_criado", user, target_type="usuario", target_id=user.id,
                  summary=f"Administrador inicial criado: {user.login}")
            return user

    def create(self, actor: User, *, login, full_name, email=None, matricula=None, phone=None,
               role=C.ROLE_ALUNO, password: str | None = None) -> tuple[User, str | None]:
        """Cria usuário. Sem senha informada, gera senha provisória (troca obrigatória)."""
        require_admin(actor)
        if role not in C.ROLES:
            raise ValidationError("Perfil inválido.", field="perfil")
        temp = None
        with self.p.engine.begin() as conn:
            data = self._validate_identity(conn, login=login, full_name=full_name, email=email, matricula=matricula, phone=phone)
            if password:
                security.validate_password_strength(password, login=data["login"])
                must_change = True
            else:
                temp = password = security.generate_temp_password()
                must_change = True
            user = self._insert(conn, data=data, role=role, password=password, must_change=must_change, created_by=actor.id)
            audit(conn, C.LOG_USUARIO, "usuario_criado", actor, target_type="usuario", target_id=user.id,
                  summary=f"{C.ROLES[role]} criado: {user.full_name} ({user.login})", perfil=role)
        return user, temp

    def import_students_csv(self, actor: User, csv_text: str) -> list[dict]:
        """Importa alunos em lote. Colunas: nome, matricula, email, telefone (opcional), login (opcional)."""
        require_admin(actor)
        reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")), delimiter=";" if csv_text.count(";") > csv_text.count(",") else ",")
        fields = {(f or "").strip().lower() for f in (reader.fieldnames or [])}
        if "nome" not in fields:
            raise ValidationError("O CSV precisa ter ao menos a coluna “nome” (e preferencialmente “matricula” e “email”).")
        report = []
        for i, raw in enumerate(reader, start=2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
            login = row.get("login") or row.get("matricula") or (row.get("email") or "").split("@")[0]
            try:
                user, temp = self.create(
                    actor, login=login, full_name=row.get("nome", ""), email=row.get("email"),
                    matricula=row.get("matricula"), phone=row.get("telefone"), role=C.ROLE_ALUNO,
                )
                report.append({"linha": i, "nome": user.full_name, "login": user.login, "senha_provisoria": temp, "resultado": "Criado"})
            except ValidationError as exc:
                report.append({"linha": i, "nome": row.get("nome", ""), "login": login, "senha_provisoria": "", "resultado": exc.message})
        return report

    def self_register(self, code: str, *, login, full_name, email, matricula, password) -> User:
        expected = str(self.p.admin.get_setting("self_registration_code") or "").strip()
        if not expected:
            raise PermissionDenied("O autocadastro está desativado. Solicite sua conta à administração da disciplina.")
        if not security.constant_time_equals((code or "").strip(), expected):
            raise PermissionDenied("Código da turma inválido.")
        if not (matricula or "").strip():
            raise ValidationError("Informe sua matrícula.", field="matricula")
        with self.p.engine.begin() as conn:
            data = self._validate_identity(conn, login=login, full_name=full_name, email=email, matricula=matricula, phone=None)
            security.validate_password_strength(password, login=data["login"])
            user = self._insert(conn, data=data, role=C.ROLE_ALUNO, password=password, must_change=False, created_by=None)
            audit(conn, C.LOG_USUARIO, "autocadastro", user, target_type="usuario", target_id=user.id,
                  summary=f"Aluno cadastrado com código da turma: {user.full_name}")
        return user

    # ------------------------------------------------------------------ #
    # Edição
    # ------------------------------------------------------------------ #
    def update_profile(self, actor: User, user_id: str, *, full_name=None, public_name=None, email=None,
                       matricula=None, phone=None, login=None) -> User:
        require_user(actor)
        is_self = actor.id == user_id
        if not actor.is_admin and not is_self:
            raise PermissionDenied()
        with self.p.engine.begin() as conn:
            cur = self._get(conn, user_id)
            if not actor.is_admin:
                # O aluno só altera dados de contato e o nome de exibição pública.
                full_name, matricula, login = cur.full_name, cur.matricula, cur.login
            data = self._validate_identity(
                conn,
                login=login if login is not None else cur.login,
                full_name=full_name if full_name is not None else cur.full_name,
                email=email if email is not None else cur.email,
                matricula=matricula if matricula is not None else cur.matricula,
                phone=phone if phone is not None else cur.phone,
                exclude_id=user_id,
            )
            pub = clean_text(public_name if public_name is not None else cur.public_name, max_len=200,
                             field="nome_publico", label="Nome exibido") or None
            changes = {k: v for k, v in {**data, "public_name": pub}.items() if getattr(cur, k) != v}
            if changes:
                conn.execute(db.users.update().where(db.users.c.id == user_id).values(**changes, updated_at=db.utcnow()))
                audit(conn, C.LOG_USUARIO, "usuario_editado", actor, target_type="usuario", target_id=user_id,
                      summary=f"Dados alterados: {cur.full_name}", campos=sorted(changes))
            return self._get(conn, user_id)

    def set_role(self, actor: User, user_id: str, role: str) -> User:
        require_admin(actor)
        if role not in C.ROLES:
            raise ValidationError("Perfil inválido.")
        with self.p.engine.begin() as conn:
            cur = self._get(conn, user_id)
            if cur.role == role:
                return cur
            if cur.role == C.ROLE_ADMIN and cur.active and self.admin_count(conn) <= 1:
                raise ConflictError("Não é possível remover o último administrador ativo. Autorize outro administrador antes.")
            conn.execute(db.users.update().where(db.users.c.id == user_id).values(role=role, updated_at=db.utcnow()))
            self._revoke_sessions(conn, user_id)
            audit(conn, C.LOG_USUARIO, "perfil_alterado", actor, target_type="usuario", target_id=user_id,
                  summary=f"Perfil de {cur.full_name}: {C.ROLES[cur.role]} → {C.ROLES[role]}", de=cur.role, para=role)
            return self._get(conn, user_id)

    def set_active(self, actor: User, user_id: str, active: bool) -> User:
        """Ativa/desativa. As submissões e publicações do usuário são preservadas."""
        require_admin(actor)
        if actor.id == user_id and not active:
            raise ConflictError("Você não pode desativar a própria conta.")
        with self.p.engine.begin() as conn:
            cur = self._get(conn, user_id)
            if cur.active == active:
                return cur
            if not active and cur.role == C.ROLE_ADMIN and self.admin_count(conn) <= 1:
                raise ConflictError("Não é possível desativar o último administrador ativo.")
            conn.execute(db.users.update().where(db.users.c.id == user_id).values(active=active, updated_at=db.utcnow()))
            if not active:
                self._revoke_sessions(conn, user_id)
            audit(conn, C.LOG_USUARIO, "conta_ativada" if active else "conta_desativada", actor,
                  target_type="usuario", target_id=user_id,
                  summary=f"Conta {'ativada' if active else 'desativada'}: {cur.full_name}")
            return self._get(conn, user_id)

    def reset_password(self, actor: User, user_id: str) -> str:
        require_admin(actor)
        temp = security.generate_temp_password()
        with self.p.engine.begin() as conn:
            cur = self._get(conn, user_id)
            conn.execute(
                db.users.update().where(db.users.c.id == user_id).values(
                    password_hash=security.hash_password(temp), must_change_password=True,
                    failed_attempts=0, locked_until=None, updated_at=db.utcnow(),
                )
            )
            self._revoke_sessions(conn, user_id)
            audit(conn, C.LOG_USUARIO, "senha_redefinida", actor, target_type="usuario", target_id=user_id,
                  summary=f"Senha provisória gerada para {cur.full_name}")
        return temp

    def change_password(self, actor: User, current: str, new: str, *, keep_token: str | None = None) -> None:
        require_user(actor)
        with self.p.engine.begin() as conn:
            row = conn.execute(sa.select(db.users.c.password_hash).where(db.users.c.id == actor.id)).first()
            if row is None or not security.verify_password(current or "", row[0]):
                raise ValidationError("A senha atual está incorreta.", field="senha_atual")
            if current == new:
                raise ValidationError("A nova senha deve ser diferente da atual.", field="senha")
            security.validate_password_strength(new, login=actor.login)
            conn.execute(
                db.users.update().where(db.users.c.id == actor.id).values(
                    password_hash=security.hash_password(new), must_change_password=False, updated_at=db.utcnow()
                )
            )
            # Encerra as outras sessões abertas com a senha antiga.
            stmt = db.sessions.update().where(db.sessions.c.user_id == actor.id)
            if keep_token:
                stmt = stmt.where(db.sessions.c.token_hash != security.hash_token(keep_token))
            conn.execute(stmt.values(revoked=True))
            audit(conn, C.LOG_USUARIO, "senha_alterada", actor, target_type="usuario", target_id=actor.id,
                  summary="Senha alterada pelo próprio usuário")

    # ------------------------------------------------------------------ #
    # Autenticação e sessões
    # ------------------------------------------------------------------ #
    def login(self, login: str, password: str) -> tuple[User, str]:
        login_n = normalize_login(login)
        now = db.utcnow()
        error: AuthError | None = None
        user: User | None = None
        token: str | None = None
        with self.p.engine.begin() as conn:
            row = conn.execute(sa.select(db.users).where(db.users.c.login == login_n)).first()
            if row is None:
                security.verify_password(password or "", security.DUMMY_HASH)  # tempo constante
                audit(conn, C.LOG_USUARIO, "login_falhou", None, actor_login=login_n[:120], summary="Login inexistente")
                error = AuthError("Login ou senha inválidos.")
            else:
                m = row._mapping
                if m["locked_until"] and m["locked_until"] > now:
                    audit(conn, C.LOG_USUARIO, "login_bloqueado", None, actor_login=login_n,
                          target_type="usuario", target_id=m["id"], summary="Tentativa durante bloqueio temporário")
                    error = AuthError("Acesso temporariamente bloqueado por excesso de tentativas. Tente novamente mais tarde.")
                elif not security.verify_password(password or "", m["password_hash"]):
                    failed = (m["failed_attempts"] or 0) + 1
                    values = {"failed_attempts": failed}
                    if failed >= MAX_FAILED:
                        values = {"failed_attempts": 0, "locked_until": now + timedelta(minutes=LOCK_MINUTES)}
                    conn.execute(db.users.update().where(db.users.c.id == m["id"]).values(**values))
                    audit(conn, C.LOG_USUARIO, "login_falhou", None, actor_login=login_n, target_type="usuario",
                          target_id=m["id"], summary="Senha incorreta" + (" — conta bloqueada por 15 min" if failed >= MAX_FAILED else ""))
                    error = AuthError("Login ou senha inválidos.")
                elif not m["active"]:
                    audit(conn, C.LOG_USUARIO, "login_conta_inativa", None, actor_login=login_n,
                          target_type="usuario", target_id=m["id"], summary="Tentativa de acesso com conta desativada")
                    error = AuthError("Conta desativada. Procure a administração da disciplina.")
                else:
                    conn.execute(
                        db.users.update().where(db.users.c.id == m["id"]).values(
                            failed_attempts=0, locked_until=None, last_login_at=now
                        )
                    )
                    token = security.new_session_token()
                    conn.execute(
                        db.sessions.insert().values(
                            token_hash=security.hash_token(token), user_id=m["id"], created_at=now,
                            expires_at=now + timedelta(hours=self.p.settings.session_hours),
                            last_seen_at=now, revoked=False,
                        )
                    )
                    user = self._get(conn, m["id"])
                    audit(conn, C.LOG_USUARIO, "login", user, target_type="usuario", target_id=user.id,
                          summary=f"Início de sessão ({C.ROLES.get(user.role, user.role)})")
        if error:
            raise error
        return user, token  # type: ignore[return-value]

    def resolve_session(self, token: str | None) -> User | None:
        """Valida o token a cada execução e relê o perfil do banco (nunca do navegador)."""
        if not token or len(token) > 200:
            return None
        th = security.hash_token(token)
        now = db.utcnow()
        with self.p.engine.connect() as conn:
            row = conn.execute(
                sa.select(db.sessions, db.users.c.active)
                .join(db.users, db.users.c.id == db.sessions.c.user_id)
                .where(db.sessions.c.token_hash == th)
            ).first()
            if row is None:
                return None
            m = row._mapping
            if m["revoked"] or m["expires_at"] <= now or not m["active"]:
                return None
            if m["last_seen_at"] < now - timedelta(hours=IDLE_HOURS):
                return None
            user = self._get(conn, m["user_id"])
        if m["last_seen_at"] < now - timedelta(minutes=5):
            with self.p.engine.begin() as conn:
                conn.execute(db.sessions.update().where(db.sessions.c.token_hash == th).values(last_seen_at=now))
        return user

    def logout(self, token: str | None, actor: User | None = None) -> None:
        if not token:
            return
        with self.p.engine.begin() as conn:
            conn.execute(
                db.sessions.update().where(db.sessions.c.token_hash == security.hash_token(token)).values(revoked=True)
            )
            if actor:
                audit(conn, C.LOG_USUARIO, "logout", actor, target_type="usuario", target_id=actor.id, summary="Fim de sessão")

    def _revoke_sessions(self, conn, user_id: str) -> None:
        conn.execute(db.sessions.update().where(db.sessions.c.user_id == user_id).values(revoked=True))

    def log_admin_access(self, actor: User, area: str) -> None:
        require_admin(actor)
        with self.p.engine.begin() as conn:
            audit(conn, C.LOG_USUARIO, "acesso_administrativo", actor, summary=f"Acesso à administração: {area}")
