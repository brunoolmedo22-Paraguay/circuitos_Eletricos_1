"""Tipos e utilitários compartilhados pelos serviços."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime

import sqlalchemy as sa

from .. import constants as C
from .. import db
from ..errors import PermissionDenied, ValidationError


@dataclass(frozen=True)
class User:
    id: str
    login: str
    full_name: str
    public_name: str | None
    email: str | None
    matricula: str | None
    phone: str | None
    role: str
    active: bool
    must_change_password: bool
    created_at: datetime | None = None
    last_login_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == C.ROLE_ADMIN and self.active

    @property
    def is_student(self) -> bool:
        return self.role == C.ROLE_ALUNO and self.active

    @property
    def display_name(self) -> str:
        return (self.public_name or self.full_name or self.login).strip()


def row_to_user(row) -> User:
    m = row._mapping
    return User(
        id=m["id"],
        login=m["login"],
        full_name=m["full_name"],
        public_name=m["public_name"],
        email=m["email"],
        matricula=m["matricula"],
        phone=m["phone"],
        role=m["role"],
        active=bool(m["active"]),
        must_change_password=bool(m["must_change_password"]),
        created_at=m["created_at"],
        last_login_at=m["last_login_at"],
    )


def require_user(actor: User | None) -> User:
    if actor is None or not actor.active:
        raise PermissionDenied("Entre com sua conta para continuar.")
    return actor


def require_admin(actor: User | None) -> User:
    if actor is None or not actor.is_admin:
        raise PermissionDenied("Acesso restrito à administração da disciplina.")
    return actor


def require_student(actor: User | None) -> User:
    if actor is None or not actor.is_student:
        raise PermissionDenied("Somente alunos podem realizar esta operação.")
    return actor


_SENSITIVE = re.compile(r"(senha|password|token|secret|hash|chave|key)", re.I)


def _sanitize(value):
    if isinstance(value, dict):
        return {k: ("[omitido]" if _SENSITIVE.search(str(k)) else _sanitize(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def audit(
    conn: sa.Connection,
    category: str,
    action: str,
    actor: User | None,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    summary: str = "",
    actor_login: str | None = None,
    **details,
) -> None:
    """Registra um evento de auditoria na mesma transação da operação."""
    conn.execute(
        db.audit_log.insert().values(
            ts=db.utcnow(),
            category=category,
            action=action,
            actor_id=actor.id if actor else None,
            actor_login=(actor.login if actor else actor_login),
            target_type=target_type,
            target_id=target_id,
            summary=summary[:500],
            details_json=json.dumps(_sanitize(details), ensure_ascii=False, default=str),
        )
    )


def clean_text(value: str | None, *, max_len: int, field: str, label: str, required: bool = False) -> str:
    text = (value or "").strip()
    if required and not text:
        raise ValidationError(f"Preencha o campo “{label}”.", field=field)
    if len(text) > max_len:
        raise ValidationError(f"O campo “{label}” aceita no máximo {max_len} caracteres.", field=field)
    return text


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
