"""
Circuitos Eléctricos I — Guía Interactiva de Aprendizaje
Portada (landing) de la plataforma educativa · UNILA

Versión 0.1 — sólo arquitectura y portada.
Los módulos de contenido se desarrollan en versiones posteriores.
"""

import streamlit as st

from utils import (
    SECTIONS,
    configure_page,
    load_global_style,
    render_sidebar,
)
from utils.helpers import data_uri

# --------------------------------------------------------------------------- #
# Configuración y estilo
# --------------------------------------------------------------------------- #
configure_page()
load_global_style()
render_sidebar(active="home")


# --------------------------------------------------------------------------- #
# Construcción del HTML de las tarjetas
# --------------------------------------------------------------------------- #
def _card_html(section: dict) -> str:
    """Genera el HTML de una tarjeta clicable a partir de una sección.

    El enlace es relativo (el *slug* de la página) para que la navegación
    funcione igual en local y en Streamlit Cloud.
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
    """Renderiza la portada completa (columna de marca + panel de tarjetas)."""
    logo = data_uri("logo_unila.png")
    cards = "".join(_card_html(sec) for sec in SECTIONS)

    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-left">
            <img class="brand-logo" src="{logo}" alt="UNILA" />
            <h1 class="hero-title">Circuitos <span class="amp">Eléctricos</span> I</h1>
            <p class="hero-sub">Guía Interactiva de Aprendizaje</p>
            <div class="hero-rule"></div>
            <p class="hero-author">
              Desarrollado por el Monitor<br>
              <strong>Bruno Manuel Olmedo Chavez</strong>
            </p>
          </div>

          <div class="hero-right">
            <div class="panel">
              <div class="card-grid">
                {cards}
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_landing()
