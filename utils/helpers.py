"""
Funções e dados compartilhados por toda a plataforma.

Centraliza aqui tudo o que as páginas precisam em comum (rotas, carregamento de
imagens, injeção de CSS, configuração da página e navegação) para que os
módulos de conteúdo fiquem limpos e sem duplicação.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

# --------------------------------------------------------------------------- #
# Rotas relativas ao projeto (funcionam localmente, no GitHub e no Streamlit Cloud)
# --------------------------------------------------------------------------- #
ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
STYLES_DIR = ROOT_DIR / "styles"

# --------------------------------------------------------------------------- #
# Identidade da aplicação
# --------------------------------------------------------------------------- #
APP_TITLE = "Circuitos Elétricos I"
APP_ICON = "⚡"
APP_VERSION = "0.4"

# Definição única das seções. Cada página e a tela inicial leem daqui,
# assim adicionar um novo módulo exige alterar apenas uma lista.
SECTIONS = [
    {
        "key": "teoria",
        "page": "pages/teoria.py",
        "slug": "teoria",
        "icon": "📘",
        "image": "teoria.png",
        "title": "Aprenda a Teoria",
        "description": (
            "Consulte definições, equações, convenções e referências dos "
            "conteúdos trabalhados em Circuitos Elétricos I."
        ),
    },
    {
        "key": "interaja",
        "page": "pages/interaja.py",
        "slug": "interaja",
        "icon": "🎛️",
        "image": "interaja.png",
        "title": "Interaja com a Teoria",
        "description": (
            "Experimente simulações dinâmicas modificando parâmetros e "
            "observando o comportamento elétrico dos circuitos."
        ),
    },
    {
        "key": "formularios",
        "page": "pages/formularios.py",
        "slug": "formularios",
        "icon": "📐",
        "image": "formularios.png",
        "title": "Formulários",
        "description": (
            "Consulte rapidamente equações, relações fundamentais e "
            "expressões matemáticas da disciplina."
        ),
    },
    {
        "key": "exercicios",
        "page": "pages/exercicios.py",
        "slug": "exercicios",
        "icon": "✅",
        "image": "exercicios.png",
        "title": "Exercícios Resolvidos",
        "description": (
            "Estude exercícios completamente desenvolvidos com explicações "
            "passo a passo e equações em LaTeX."
        ),
    },
]

# --------------------------------------------------------------------------- #
# Recursos (imagens e CSS)
# --------------------------------------------------------------------------- #

def asset_b64(filename: str) -> str:
    """Retorna uma imagem de ``assets/`` como string base64 pronta para um data URI.

    O resultado é armazenado em cache porque as mesmas imagens são incorporadas em cada renderização da
    página inicial. Se o arquivo não existir, retorna uma string vazia para não quebrar o app.
    """
    path = ASSETS_DIR / filename
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def data_uri(filename: str, mime: str = "image/png") -> str:
    """Data URI completo para incorporar uma imagem em HTML/CSS."""
    b64 = asset_b64(filename)
    return f"data:{mime};base64,{b64}" if b64 else ""



def _read_css() -> str:
    css_path = STYLES_DIR / "main.css"
    return css_path.read_text(encoding="utf-8") if css_path.exists() else ""


# --------------------------------------------------------------------------- #
# Configuração e estilo global
# --------------------------------------------------------------------------- #
def configure_page(subtitle: str | None = None) -> None:
    """Aplica ``st.set_page_config`` de forma homogênea em todas as páginas."""
    page_title = f"{APP_TITLE} · {subtitle}" if subtitle else APP_TITLE
    st.set_page_config(
        page_title=page_title,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def load_global_style() -> None:
    """Injeta o CSS global (paleta, tipografia, layout e componentes)."""
    css = _read_css()
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_html(html: str) -> None:
    """Injeta HTML no app de forma segura.

    O Streamlit processa ``st.markdown`` com um parser Markdown: se alguma linha do
    HTML estiver indentada (4+ espaços), ela é interpretada como bloco de código e
    exibida como texto literal. Aqui removemos a indentação de cada linha (e as
    linhas vazias) para que o bloco seja sempre renderizado como HTML.
    """
    cleaned = "\n".join(line.lstrip() for line in html.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Navegação
# --------------------------------------------------------------------------- #
def render_sidebar(active: str | None = None) -> None:
    """Barra lateral de navegação própria (substitui a lista automática).

    ``active`` é a chave da seção atual, para não criar um link para ela mesma.
    """
    with st.sidebar:
        st.markdown(
            f"<div class='side-brand'>{APP_ICON} {APP_TITLE}</div>",
            unsafe_allow_html=True,
        )
        st.page_link("app.py", label="Início", icon="🏠")
        for sec in SECTIONS:
            st.page_link(sec["page"], label=sec["title"], icon=sec["icon"])
        st.markdown(
            f"<div class='side-foot'>Monitoria · UNILA<br>Versão {APP_VERSION}</div>",
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# Conteúdo temporário para módulos ainda não desenvolvidos
# --------------------------------------------------------------------------- #
def render_placeholder(section_key: str) -> None:
    """Estado 'em construção' consistente para as páginas da v0.1."""
    sec = next((s for s in SECTIONS if s["key"] == section_key), None)
    if sec is None:
        st.error("Seção não encontrada.")
        return

    icon_uri = data_uri(sec["image"])
    render_html(
        f"""
        <div class="page-hero">
          <div class="page-hero__badge">
            {f'<img src="{icon_uri}" alt="" />' if icon_uri else sec['icon']}
          </div>
          <div class="page-hero__text">
            <span class="eyebrow">Módulo</span>
            <h1>{sec['title']}</h1>
            <p>{sec['description']}</p>
          </div>
        </div>

        <div class="build-note">
          <span class="build-note__tag">Em construção</span>
          <p>Este módulo faz parte do roteiro de desenvolvimento da plataforma e será
          desenvolvido em uma próxima versão. A estrutura já está pronta para
          receber o conteúdo.</p>
        </div>
        """
    )
    st.page_link("app.py", label="Voltar ao início", icon=":material/arrow_back:")
