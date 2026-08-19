"""Estrutura vazia do módulo ``Aprenda la Teoría``.

A seção mantém somente o diretório das unidades. Todo o conteúdo teórico,
artigos, tópicos, busca, gráficos e referências foi removido intencionalmente.
"""

from __future__ import annotations

from html import escape
from urllib.parse import quote

import streamlit as st

from utils import configure_page, load_global_style, render_html


configure_page(subtitle="Aprenda la Teoría")
load_global_style()


UNITS = (
    ("fundamentos-cc", 1, "Fundamentos de circuitos en CC"),
    ("circuitos-resistivos", 2, "Circuitos resistivos"),
    ("metodos-cc", 3, "Métodos de análisis en CC"),
    ("teoremas", 4, "Teoremas de circuitos"),
    ("capacitores-inductores", 5, "Capacitores e inductores"),
    ("introduccion-ca", 6, "Introducción a corriente alternada"),
    ("circuitos-potencia-ca", 7, "Circuitos y potencia en CA"),
)


def _query_value(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _render_directory() -> None:
    selected = _query_value("unit") or UNITS[0][0]
    if selected not in {unit[0] for unit in UNITS}:
        selected = UNITS[0][0]

    cards = "".join(
        f"""
        <a class="theory-directory__item {'is-active' if key == selected else ''}"
           href="?unit={quote(key)}" target="_self">
          <span>UNIDAD {number:02d}</span>
          <strong>{escape(title)}</strong>
        </a>
        """
        for key, number, title in UNITS
    )

    render_html(
        f"""
        <div class="theory-empty-page-marker" aria-hidden="true"></div>
        <nav class="theory-directory" aria-label="Directorio de unidades">
          {cards}
        </nav>
        """
    )


_render_directory()
