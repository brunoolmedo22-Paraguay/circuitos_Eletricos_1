"""Ponto de entrada da interface do módulo Exercícios Resolvidos."""

from __future__ import annotations

import streamlit as st

from .. import constants as C
from ..services import Platform, User
from . import views_admin, views_auth, views_public, views_student
from .runtime import get_platform, get_settings, guarded, nav_to, param, show_flash, sign_out, current_user
from .widgets import esc, md

STUDENT_VIEWS = {"submeter", "minhas", "submissao"}
LOGGED_VIEWS = {"propostos", "conta", "senha"} | STUDENT_VIEWS
ADMIN_VIEWS = {"admin"}

BREADCRUMB = {
    None: "Biblioteca",
    "resolucao": "Resolução",
    "entrar": "Entrar",
    "configuracao": "Configuração inicial",
    "cadastro": "Criar conta",
    "senha": "Trocar senha",
    "conta": "Minha conta",
    "propostos": "Exercícios Propostos",
    "submeter": "Submeter Resolução",
    "minhas": "Minhas Submissões",
    "submissao": "Minhas Submissões",
    "admin": "Administração",
}


def _config_screen(problems: list[str]) -> None:
    md(
        """
        <div class="ex-config">
          <span class="ex-config__tag">Configuração pendente</span>
          <h2>O módulo Exercícios Resolvidos ainda não está pronto para receber entregas</h2>
          <p>Para proteger os trabalhos dos alunos, a plataforma não aceita submissões enquanto o
          armazenamento persistente não estiver configurado. Nada foi perdido: o restante da
          plataforma continua funcionando normalmente.</p>
        </div>
        """
    )
    with st.expander("Detalhes para a administração", expanded=False):
        for pr in problems:
            st.markdown(f"- {pr}")
        st.markdown(
            "Siga o guia `docs/INSTALACAO.md` (seções *Supabase* e *Segredos do Streamlit Cloud*). "
            "Para testar localmente sem serviços externos, use `[app] mode = \"demonstracao\"`."
        )


def _session_bar(p: Platform, user: User | None, view: str | None) -> None:
    left, right = st.columns([5, 3], vertical_alignment="center")
    with left:
        trail = '<span class="ex-crumb__root">Exercícios Resolvidos</span>'
        if view:
            trail += f'<span class="ex-crumb__sep">/</span><span>{esc(BREADCRUMB.get(view, ""))}</span>'
        md(f'<nav class="ex-crumb" aria-label="Você está em">{trail}</nav>')
    with right, st.container(key="ex-sessionbar"):
        if user:
            cols = st.columns([3, 1.3], vertical_alignment="center")
            with cols[0]:
                md(
                    f'<div class="ex-user"><span class="ex-user__avatar">{esc(user.display_name[:1].upper())}</span>'
                    f'<span class="ex-user__name">{esc(user.display_name)}</span>'
                    f'<span class="ex-user__role">{esc(C.ROLES[user.role])}</span></div>'
                )
            with cols[1]:
                if st.button("Sair", key="bar-logout", use_container_width=True):
                    sign_out(p, user)
                    nav_to(None)
                    st.rerun()
        else:
            cols = st.columns([2, 1.3])
            with cols[1]:
                st.button("Entrar", key="bar-login", type="primary", use_container_width=True,
                          on_click=nav_to, args=("entrar",))


def _fab(user: User | None, bootstrap: bool) -> None:
    """Botão flutuante de ações (canto inferior direito)."""
    with st.container(key="ce1-fab"):
        with st.popover("Ações", icon=":material/add:"):
            md('<div class="ex-fab__title">Exercícios Resolvidos</div>')
            is_admin = bool(user and user.is_admin)
            if not is_admin:
                st.button("01 · Submeter Resolução", key="fab-sub", use_container_width=True,
                          on_click=nav_to, args=("submeter",) if user else ("entrar",),
                          kwargs={} if user else {"next": "submeter"})
                st.button("02 · Alterar Resolução", key="fab-alt", use_container_width=True,
                          on_click=nav_to, args=("minhas",) if user else ("entrar",),
                          kwargs={} if user else {"next": "minhas"})
            if is_admin:
                md('<div class="ex-fab__group">03 · Administração</div>')
                for sec, label in views_admin.SECTIONS:
                    st.button(label, key=f"fab-adm-{sec}", use_container_width=True,
                              on_click=nav_to, args=("admin",), kwargs={"a": sec})
            md('<div class="ex-fab__sep"></div>')
            st.button("Biblioteca de resoluções", key="fab-lib", use_container_width=True, on_click=nav_to, args=(None,))
            if user:
                st.button("Exercícios Propostos", key="fab-prop", use_container_width=True, on_click=nav_to, args=("propostos",))
                st.button("Minha conta", key="fab-conta", use_container_width=True, on_click=nav_to, args=("conta",))
            else:
                st.button("Entrar", key="fab-login", use_container_width=True, on_click=nav_to, args=("entrar",))


def run() -> None:
    settings = get_settings()
    problems = settings.problems()
    if problems:
        _config_screen(problems)
        return

    try:
        p = get_platform()
    except Exception:
        import logging

        logging.getLogger("ce1.ui").exception("Falha ao iniciar a plataforma")
        md(
            """
            <div class="ex-config">
              <span class="ex-config__tag">Serviço indisponível</span>
              <h2>Não foi possível conectar ao banco de dados</h2>
              <p>As resoluções continuam guardadas com segurança. Tente novamente em alguns minutos.
              Se o problema persistir, um administrador deve verificar no painel do Supabase se o projeto
              foi pausado por inatividade (botão <em>Restore project</em>).</p>
            </div>
            """
        )
        return

    if settings.is_demo:
        md(
            '<div class="ex-demo" role="status"><strong>Modo demonstração.</strong> '
            "Os dados são de teste e ficam apenas neste computador. Não use para entregas reais.</div>"
        )

    user = None
    with guarded("sessão"):
        user = current_user(p)
    view = param("v")
    bootstrap = p.users.bootstrap_needed()

    _session_bar(p, user, view)
    show_flash()

    with st.container(key="ex-main"):
        with guarded(view or "catalogo"):
            if user and user.must_change_password and view not in ("senha",):
                views_auth.forced_password(p, user)
            elif view in LOGGED_VIEWS and user is None:
                views_auth.login(p, next_view=view, notice="Entre com sua conta para continuar.")
            elif view in STUDENT_VIEWS and not user.is_student:
                st.info("Esta área é destinada aos alunos. Use o menu Administração para gerenciar as entregas.")
                st.button("Ir para a Administração", on_click=nav_to, args=("admin",))
            elif view in ADMIN_VIEWS and (user is None or not user.is_admin):
                if user is None:
                    views_auth.login(p, next_view="admin", notice="Área restrita à administração da disciplina.")
                else:
                    st.warning("Acesso restrito à administração da disciplina.")
            elif view == "resolucao":
                views_public.detail(p, user, param("r"))
            elif view == "entrar":
                if user:
                    nav_to(param("next"))
                    st.rerun()
                views_auth.login(p, next_view=param("next"))
            elif view == "configuracao":
                views_auth.setup(p, user)
            elif view == "cadastro":
                views_auth.register(p, user)
            elif view == "senha":
                views_auth.forced_password(p, user)
            elif view == "conta":
                views_auth.account(p, user)
            elif view == "propostos":
                views_student.proposed(p, user)
            elif view == "submeter":
                views_student.submit(p, user, param("id"), param("ex"))
            elif view == "minhas":
                views_student.mine(p, user)
            elif view == "submissao":
                views_student.submission(p, user, param("id"))
            elif view == "admin":
                views_admin.shell(p, user, param("a") or "bandeja", param("id"))
            else:
                views_public.catalog(p, user)

    _fab(user, bootstrap)
