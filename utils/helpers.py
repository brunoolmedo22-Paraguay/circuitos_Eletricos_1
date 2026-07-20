"""
Funciones y datos compartidos por toda la plataforma.

Centraliza aquí todo lo que las páginas necesitan en común (rutas, carga de
imágenes, inyección de CSS, configuración de página y navegación) para que los
módulos de contenido queden limpios y sin duplicación.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

# --------------------------------------------------------------------------- #
# Rutas relativas al proyecto (funcionan en local, GitHub y Streamlit Cloud)
# --------------------------------------------------------------------------- #
ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
STYLES_DIR = ROOT_DIR / "styles"

# --------------------------------------------------------------------------- #
# Identidad de la aplicación
# --------------------------------------------------------------------------- #
APP_TITLE = "Circuitos Eléctricos I"
APP_ICON = "⚡"
APP_VERSION = "0.3"

# Definición única de las secciones. Cada página y la portada leen de aquí,
# así agregar un módulo nuevo es cambiar una sola lista.
SECTIONS = [
    {
        "key": "teoria",
        "page": "pages/teoria.py",
        "slug": "teoria",
        "icon": "📘",
        "image": "teoria.png",
        "title": "Aprenda la Teoría",
        "description": (
            "Consulte definiciones, ecuaciones, convenciones y referencias de "
            "los contenidos trabajados en Circuitos Eléctricos I."
        ),
    },
    {
        "key": "interactue",
        "page": "pages/interactue.py",
        "slug": "interactue",
        "icon": "🎛️",
        "image": "interactue.png",
        "title": "Interactúe con la Teoría",
        "description": (
            "Experimente con simulaciones dinámicas modificando parámetros y "
            "observando el comportamiento eléctrico de los circuitos."
        ),
    },
    {
        "key": "formularios",
        "page": "pages/formularios.py",
        "slug": "formularios",
        "icon": "📐",
        "image": "formularios.png",
        "title": "Formularios",
        "description": (
            "Consulte rápidamente ecuaciones, relaciones fundamentales y "
            "expresiones matemáticas de la disciplina."
        ),
    },
    {
        "key": "ejercicios",
        "page": "pages/ejercicios.py",
        "slug": "ejercicios",
        "icon": "✅",
        "image": "solutions.png",
        "title": "Ejercicios Resueltos",
        "description": (
            "Estudie ejercicios completamente desarrollados con explicaciones "
            "paso a paso y ecuaciones en LaTeX."
        ),
    },
]

# --------------------------------------------------------------------------- #
# Recursos (imágenes y CSS)
# --------------------------------------------------------------------------- #

def asset_b64(filename: str) -> str:
    """Devuelve una imagen de ``assets/`` como cadena base64 lista para un data URI.

    Se cachea porque las mismas imágenes se incrustan en cada renderizado de la
    portada. Si el archivo no existe devuelve cadena vacía para no romper la app.
    """
    path = ASSETS_DIR / filename
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def data_uri(filename: str, mime: str = "image/png") -> str:
    """Data URI completo para incrustar una imagen en HTML/CSS."""
    b64 = asset_b64(filename)
    return f"data:{mime};base64,{b64}" if b64 else ""



def _read_css() -> str:
    css_path = STYLES_DIR / "main.css"
    return css_path.read_text(encoding="utf-8") if css_path.exists() else ""


# --------------------------------------------------------------------------- #
# Configuración y estilo global
# --------------------------------------------------------------------------- #
def configure_page(subtitle: str | None = None) -> None:
    """Aplica ``st.set_page_config`` de forma homogénea en todas las páginas."""
    page_title = f"{APP_TITLE} · {subtitle}" if subtitle else APP_TITLE
    st.set_page_config(
        page_title=page_title,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="collapsed",
    )


def load_global_style() -> None:
    """Inyecta el CSS global (paleta, tipografía, layout y componentes)."""
    css = _read_css()
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render_html(html: str) -> None:
    """Inyecta HTML en la app de forma segura.

    Streamlit pasa ``st.markdown`` por un parser Markdown: si alguna línea del
    HTML está indentada (4+ espacios) la interpreta como bloque de código y la
    muestra como texto literal. Aquí quitamos la indentación de cada línea (y las
    líneas vacías) para que el bloque se renderice siempre como HTML.
    """
    cleaned = "\n".join(line.lstrip() for line in html.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Navegación
# --------------------------------------------------------------------------- #
def render_sidebar(active: str | None = None) -> None:
    """Barra lateral de navegación propia (reemplaza la lista automática).

    ``active`` es la clave de la sección actual, para no enlazarla a sí misma.
    """
    with st.sidebar:
        st.markdown(
            f"<div class='side-brand'>{APP_ICON} {APP_TITLE}</div>",
            unsafe_allow_html=True,
        )
        st.page_link("app.py", label="Inicio", icon="🏠")
        for sec in SECTIONS:
            st.page_link(sec["page"], label=sec["title"], icon=sec["icon"])
        st.markdown(
            f"<div class='side-foot'>Monitoría · UNILA<br>Versión {APP_VERSION}</div>",
            unsafe_allow_html=True,
        )


# --------------------------------------------------------------------------- #
# Contenido temporal para módulos aún no desarrollados
# --------------------------------------------------------------------------- #
def render_placeholder(section_key: str) -> None:
    """Estado 'en construcción' consistente para las páginas de la v0.1."""
    sec = next((s for s in SECTIONS if s["key"] == section_key), None)
    if sec is None:
        st.error("Sección no encontrada.")
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
          <span class="build-note__tag">En construcción</span>
          <p>Este módulo forma parte de la hoja de ruta de la plataforma y se
          desarrollará en una próxima versión. La estructura ya está lista para
          recibir el contenido.</p>
        </div>
        """
    )
    st.page_link("app.py", label="Volver al inicio", icon=":material/arrow_back:")
