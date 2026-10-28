"""Módulo: Exercícios Resolvidos — biblioteca colaborativa de resoluções.

Estudantes submetem resoluções (vídeo no YouTube + PDF + circuito no Falstad),
a administração avalia e somente as resoluções aprovadas são publicadas.
A lógica fica no pacote ``resolucoes``; esta página apenas monta a interface.
"""

from pathlib import Path

import streamlit as st

from utils import configure_page, load_global_style, render_sidebar

configure_page(subtitle="Exercícios Resolvidos")
load_global_style()

_page_css = Path(__file__).resolve().parent.parent / "styles" / "exercicios.css"
if _page_css.exists():
    st.markdown(f"<style>{_page_css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

render_sidebar(active="exercicios")

from resolucoes.ui.app import run  # noqa: E402

run()
