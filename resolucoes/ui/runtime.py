"""Infraestrutura da interface: plataforma, sessão, navegação e tratamento de erros."""

from __future__ import annotations

import json
import logging
import traceback
import uuid
from contextlib import contextmanager

import sqlalchemy as sa
import streamlit as st
import streamlit.components.v1 as components

from .. import constants as C
from ..config import Settings, load_settings
from ..errors import AppError, PermissionDenied
from ..services import Platform, User

log = logging.getLogger("ce1.ui")


# --------------------------------------------------------------------------- #
# Plataforma (uma instância por processo)
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def _platform_for(settings_json: str) -> Platform:
    settings = Settings(**json.loads(settings_json))
    return Platform(settings)


def get_settings() -> Settings:
    return load_settings()


def get_platform() -> Platform:
    s = get_settings()
    payload = json.dumps({k: v for k, v in s.__dict__.items() if k != "extra"}, sort_keys=True)
    return _platform_for(payload)


# --------------------------------------------------------------------------- #
# Navegação por parâmetros de URL (mantém a sessão; permite links diretos)
# --------------------------------------------------------------------------- #
def param(name: str, default: str | None = None) -> str | None:
    return st.query_params.get(name, default)


def nav_to(view: str | None = None, **params) -> None:
    """Muda de tela sem recarregar a página (usável em callbacks)."""
    st.query_params.clear()
    if view:
        st.query_params["v"] = view
    for k, v in params.items():
        if v is not None:
            st.query_params[k] = str(v)


def go(view: str | None = None, **params) -> None:
    nav_to(view, **params)
    st.rerun()


def flash(message: str, kind: str = "success") -> None:
    st.session_state.setdefault("_flash", []).append((kind, message))


def show_flash() -> None:
    for kind, msg in st.session_state.pop("_flash", []):
        {"success": st.success, "info": st.info, "warning": st.warning, "error": st.error}[kind](msg)


# --------------------------------------------------------------------------- #
# Sessão: token no servidor + cookie para sobreviver a recarregamentos
# --------------------------------------------------------------------------- #
def _cookie_script(token: str | None, max_age: int) -> str:
    if token:
        value = f"{C.SESSION_COOKIE}={token}; Max-Age={max_age}; Path=/; SameSite=Lax"
    else:
        value = f"{C.SESSION_COOKIE}=; Max-Age=0; Path=/; SameSite=Lax"
    # O iframe do componente compartilha a origem do app (allow-same-origin).
    return (
        "<script>(function(){var c=" + json.dumps(value) + ";"
        "if(window.location.protocol==='https:'||(window.parent&&window.parent.location.protocol==='https:')){c+='; Secure';}"
        "try{window.parent.document.cookie=c;}catch(e){document.cookie=c;}})();</script>"
    )


def _flush_cookie_ops() -> None:
    op = st.session_state.pop("_cookie_op", None)
    if op is None:
        return
    hours = get_settings().session_hours
    components.html(_cookie_script(op or None, hours * 3600), height=0)


def current_user(p: Platform) -> User | None:
    """Usuário autenticado, revalidado no banco a cada execução."""
    _flush_cookie_ops()
    token = st.session_state.get("_token")
    if not token and not st.session_state.get("_logged_out"):
        try:
            token = st.context.cookies.get(C.SESSION_COOKIE)
        except Exception:
            token = None
    user = p.users.resolve_session(token) if token else None
    if user is None:
        if st.session_state.get("_token"):
            st.session_state.pop("_token", None)
            st.session_state["_cookie_op"] = ""  # limpa cookie expirado
            flash("Sua sessão expirou. Entre novamente para continuar.", "warning")
        return None
    st.session_state["_token"] = token
    return user


def sign_in(p: Platform, login: str, password: str) -> User:
    user, token = p.users.login(login, password)
    st.session_state["_token"] = token
    st.session_state["_cookie_op"] = token
    st.session_state.pop("_logged_out", None)
    return user


def sign_out(p: Platform, user: User | None) -> None:
    p.users.logout(st.session_state.get("_token"), user)
    for k in list(st.session_state.keys()):
        if not k.startswith("theory") and not k.startswith("interact"):
            del st.session_state[k]
    st.session_state["_logged_out"] = True
    st.session_state["_cookie_op"] = ""


# --------------------------------------------------------------------------- #
# Tratamento de erros
# --------------------------------------------------------------------------- #
_CONTROL_FLOW = {"RerunException", "StopException", "RerunData"}


@contextmanager
def guarded(context: str = ""):
    """Converte erros em mensagens claras, sem expor detalhes internos."""
    try:
        yield
    except AppError as exc:
        if isinstance(exc, PermissionDenied):
            st.warning(exc.message)
        else:
            st.error(exc.message)
    except sa.exc.OperationalError:
        log.exception("Falha de conexão com o banco (%s)", context)
        st.error(
            "Não foi possível conectar ao banco de dados agora. Tente novamente em instantes. "
            "Se o problema persistir, um administrador deve verificar se o projeto do banco "
            "(Supabase) não foi pausado por inatividade."
        )
    except Exception as exc:  # noqa: BLE001
        if type(exc).__name__ in _CONTROL_FLOW:
            raise
        ref = uuid.uuid4().hex[:8].upper()
        log.error("Erro inesperado [%s] em %s: %s\n%s", ref, context, exc, traceback.format_exc())
        st.error(f"Ocorreu um erro inesperado. Tente novamente; se persistir, informe o código {ref} à administração.")


def run_action(fn, *args, success: str | None = None, **kwargs):
    """Executa uma ação de serviço exibindo o erro no próprio formulário."""
    try:
        result = fn(*args, **kwargs)
    except AppError as exc:
        st.error(exc.message)
        return None, False
    except sa.exc.OperationalError:
        log.exception("Falha de banco em ação")
        st.error("Não foi possível salvar: falha de conexão com o banco de dados. Nada foi alterado; tente novamente.")
        return None, False
    if success:
        flash(success)
    return result, True
