"""
Circuitos Elétricos I — Guia Interativo de Aprendizagem
Página inicial (landing) da plataforma educacional · UNILA

Versão 0.3 — página inicial e repositório de consulta teórica.
"""

import streamlit as st

from utils import (
    SECTIONS,
    configure_page,
    load_global_style,
    render_html,
    render_sidebar,
)
from utils.helpers import data_uri

# --------------------------------------------------------------------------- #
# Configuração e estilo
# --------------------------------------------------------------------------- #
configure_page()
load_global_style()
render_sidebar(active="home")


# --------------------------------------------------------------------------- #
# Construção do HTML dos cartões
# --------------------------------------------------------------------------- #
def _card_html(section: dict) -> str:
    """Gera o HTML de um cartão clicável a partir de uma seção.

    O link é relativo (o *slug* da página) para que a navegação
    funcione da mesma forma localmente e no Streamlit Cloud.
    """
    icon = data_uri(section["image"])
    return f"""
      <a class="card" href="{section['slug']}" target="_self">
        <div class="card-icon"><img src="{icon}" alt="{section['title']}" /></div>
        <div class="card-title">{section['title']}</div>
        <div class="card-desc">{section['description']}</div>
        <div class="card-cta">Explorar →</div>
      </a>
    """


def render_landing() -> None:
    """Renderiza a tela principal da plataforma."""
    logo = data_uri("logo_unila.png")
    cards = "".join(_card_html(sec) for sec in SECTIONS)

    render_html(
        f"""
        <main class="app-shell">
          <section class="left-panel">
            <img class="brand-logo" src="{logo}" alt="UNILA" />

            <h1 class="app-title">Circuitos Elétricos I</h1>
            <p class="app-subtitle">Guia Interativo de Aprendizagem</p>

            <div class="app-rule"></div>

            <p class="app-author">
              Desenvolvido pelo Monitor<br>
              <strong>Bruno Manuel Olmedo Chavez</strong>
            </p>
          </section>

          <section class="right-panel">
            <div class="cards-grid">
              {cards}
            </div>
          </section>
        </main>
        """
    )


render_landing()
