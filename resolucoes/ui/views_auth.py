"""Entrar, configuração inicial, autocadastro, troca de senha e Minha conta."""

from __future__ import annotations

import streamlit as st

from .. import constants as C
from ..errors import ValidationError
from ..services import Platform, User
from .runtime import flash, get_settings, go, nav_to, run_action, sign_in, sign_out
from .widgets import esc, md


def _card_head(title: str, text: str) -> None:
    md(f'<div class="ex-auth__head"><h2>{esc(title)}</h2><p>{esc(text)}</p></div>')


def _default_after_login(user: User) -> str | None:
    return "admin" if user.is_admin else None


def login(p: Platform, next_view: str | None = None, notice: str | None = None) -> None:
    mid = st.columns([1, 1.4, 1])[1]
    with mid, st.container(key="ex-auth"):
        _card_head("Entrar", "Use o login e a senha fornecidos pela administração da disciplina.")
        if notice:
            st.info(notice)
        with st.form("form-login"):
            login_v = st.text_input("Login", placeholder="sua matrícula ou login", autocomplete="username")
            pwd = st.text_input("Senha", type="password", autocomplete="current-password")
            ok = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        if ok:
            user, success = run_action(sign_in, p, login_v, pwd)
            if success:
                flash(f"Bem-vindo(a), {user.display_name}!")
                go(next_view or _default_after_login(user))
        st.caption("Esqueceu a senha? Peça a um administrador uma senha provisória; ela deverá ser trocada no primeiro acesso.")
        if p.admin.get_setting("self_registration_code"):
            st.button("Criar conta com o código da turma", use_container_width=True, on_click=nav_to, args=("cadastro",))
        if p.users.bootstrap_needed() and get_settings().bootstrap_token:
            st.divider()
            st.caption("Nenhum administrador foi cadastrado ainda.")
            st.button("Configuração inicial da plataforma", use_container_width=True, on_click=nav_to, args=("configuracao",))


def setup(p: Platform, user: User | None) -> None:
    mid = st.columns([1, 1.6, 1])[1]
    with mid, st.container(key="ex-auth"):
        if not p.users.bootstrap_needed():
            _card_head("Configuração concluída", "Já existe um administrador. Novos administradores são autorizados no painel.")
            st.button("Entrar", type="primary", on_click=nav_to, args=("entrar",))
            return
        _card_head(
            "Configuração inicial",
            "Cria o primeiro administrador. Informe o token de configuração definido nos segredos do servidor.",
        )
        with st.form("form-setup"):
            token = st.text_input("Token de configuração *", type="password")
            name = st.text_input("Nome completo *")
            login_v = st.text_input("Login *", help="Letras minúsculas, números, ponto, hífen ou @.")
            email = st.text_input("E-mail institucional")
            pwd = st.text_input("Senha *", type="password", help="Mínimo de 8 caracteres, combinando letras e números.")
            pwd2 = st.text_input("Confirme a senha *", type="password")
            ok = st.form_submit_button("Criar administrador", type="primary", use_container_width=True)
        if ok:
            if pwd != pwd2:
                st.error("As senhas não coincidem.")
                return
            _, success = run_action(p.users.bootstrap_admin, token, login=login_v, full_name=name, email=email, password=pwd)
            if success:
                sign_in(p, login_v, pwd)
                flash("Administrador criado. Agora autorize o segundo administrador em Administração → Adicionar Usuários.")
                go("admin", a="usuarios_novo")


def register(p: Platform, user: User | None) -> None:
    mid = st.columns([1, 1.6, 1])[1]
    with mid, st.container(key="ex-auth"):
        if not p.admin.get_setting("self_registration_code"):
            _card_head("Autocadastro desativado", "Solicite sua conta à administração da disciplina.")
            return
        _card_head("Criar conta de aluno", "Use o código da turma informado pelo professor ou pelo monitor.")
        with st.form("form-register"):
            code = st.text_input("Código da turma *", type="password")
            name = st.text_input("Nome completo *")
            mat = st.text_input("Matrícula *")
            email = st.text_input("E-mail")
            login_v = st.text_input("Login *", help="Sugestão: sua matrícula.")
            pwd = st.text_input("Senha *", type="password", help="Mínimo de 8 caracteres, com letras e números.")
            pwd2 = st.text_input("Confirme a senha *", type="password")
            st.caption(
                "Seus dados são usados apenas para identificar suas entregas. Seu nome só aparece publicamente "
                "nas resoluções aprovadas que você autorizar no momento do envio."
            )
            ok = st.form_submit_button("Criar conta", type="primary", use_container_width=True)
        if ok:
            if pwd != pwd2:
                st.error("As senhas não coincidem.")
                return
            _, success = run_action(p.users.self_register, code, login=login_v, full_name=name, email=email,
                                    matricula=mat, password=pwd)
            if success:
                sign_in(p, login_v, pwd)
                flash("Conta criada. Escolha um exercício proposto para começar.")
                go("propostos")


def _password_form(p: Platform, user: User, key: str) -> None:
    with st.form(key):
        cur = st.text_input("Senha atual", type="password", autocomplete="current-password")
        new = st.text_input("Nova senha", type="password", autocomplete="new-password",
                            help="Mínimo de 8 caracteres, combinando letras e números.")
        new2 = st.text_input("Confirme a nova senha", type="password", autocomplete="new-password")
        ok = st.form_submit_button("Alterar senha", type="primary")
    if ok:
        if new != new2:
            st.error("As senhas não coincidem.")
            return
        _, success = run_action(p.users.change_password, user, cur, new, keep_token=st.session_state.get("_token"))
        if success:
            flash("Senha alterada. As outras sessões abertas foram encerradas.")
            go(_default_after_login(user) if key == "form-forced" else "conta")


def forced_password(p: Platform, user: User) -> None:
    mid = st.columns([1, 1.5, 1])[1]
    with mid, st.container(key="ex-auth"):
        _card_head("Defina sua senha", "Você entrou com uma senha provisória. Escolha uma senha pessoal para continuar.")
        _password_form(p, user, "form-forced")
        if st.button("Sair", key="forced-out"):
            sign_out(p, user)
            go(None)


def account(p: Platform, user: User) -> None:
    md(f'<div class="ex-head"><div><div class="ex-head__kicker">Minha conta</div><h2>{esc(user.full_name)}</h2>'
       f'<p>{esc(C.ROLES[user.role])} · login <strong>{esc(user.login)}</strong>'
       f'{" · matrícula " + esc(user.matricula) if user.matricula else ""}</p></div></div>')
    c1, c2 = st.columns(2, gap="large")
    with c1, st.container(key="ex-panel-conta"):
        md('<div class="ex-panel__label">Contato e exibição pública</div>')
        with st.form("form-profile"):
            pub = st.text_input("Nome exibido nas resoluções publicadas", value=user.public_name or "",
                                placeholder=user.full_name, help="Deixe em branco para usar o nome completo.")
            email = st.text_input("E-mail", value=user.email or "")
            phone = st.text_input("WhatsApp (opcional)", value=user.phone or "", placeholder="+5545999998888",
                                  help="Usado apenas pela administração para enviar avisos sobre suas entregas.")
            ok = st.form_submit_button("Salvar dados")
        if ok:
            _, success = run_action(p.users.update_profile, user, user.id, public_name=pub, email=email, phone=phone,
                                    success="Dados atualizados.")
            if success:
                st.rerun()
    with c2, st.container(key="ex-panel-senha"):
        md('<div class="ex-panel__label">Senha</div>')
        _password_form(p, user, "form-change")
    if st.button("Sair da conta", key="acc-out"):
        sign_out(p, user)
        go(None)


__all__ = ["login", "setup", "register", "forced_password", "account", "ValidationError"]
