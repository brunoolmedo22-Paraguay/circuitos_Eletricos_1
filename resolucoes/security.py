"""Primitivas de segurança: hash de senhas, tokens de sessão e política de senha.

Usa apenas a biblioteca padrão (``hashlib.scrypt``), sem dependências pagas ou
serviços externos. As senhas nunca são armazenadas nem registradas em texto puro.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import string

from .errors import ValidationError

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_DKLEN)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


# Hash fixo usado para equalizar o tempo de resposta quando o login não existe.
DUMMY_HASH = hash_password(secrets.token_urlsafe(12))


def validate_password_strength(password: str, *, login: str = "") -> None:
    if len(password) < 8:
        raise ValidationError("A senha deve ter pelo menos 8 caracteres.", field="senha")
    if len(password) > 128:
        raise ValidationError("A senha deve ter no máximo 128 caracteres.", field="senha")
    if not re.search(r"[A-Za-zÀ-ÿ]", password) or not re.search(r"\d", password):
        raise ValidationError("A senha deve combinar letras e números.", field="senha")
    if login and password.strip().lower() == login.strip().lower():
        raise ValidationError("A senha não pode ser igual ao login.", field="senha")


_TEMP_ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0OolI1")


def generate_temp_password(length: int = 10) -> str:
    """Senha provisória legível; o usuário é obrigado a trocá-la no primeiro acesso."""
    while True:
        pwd = "".join(secrets.choice(_TEMP_ALPHABET) for _ in range(length))
        if re.search(r"[A-Za-z]", pwd) and re.search(r"\d", pwd):
            return pwd


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
