"""
Circuitos Eléctricos I — Guía Interactiva de Aprendizaje
Portada (landing) de la plataforma educativa · UNILA

Versión 0.3 — portada y repositorio de consulta teórica.
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
    """Renderiza la pantalla principal de la plataforma."""
    logo = data_uri("logo_unila.png")
    cards = "".join(_card_html(sec) for sec in SECTIONS)

    render_html(
        f"""
        <main class="app-shell">
          <section class="left-panel">
            <img class="brand-logo" src="{logo}" alt="UNILA" />

            <h1 class="app-title">Circuitos Eléctricos I</h1>
            <p class="app-subtitle">Guía Interactiva de Aprendizaje</p>

            <div class="app-rule"></div>

            <p class="app-author">
              Desarrollado por el Monitor<br>
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
