"""Apresentação de um exercício proposto: enunciado, figura, descrição e materiais.

Usado em todas as telas em que um exercício aparece (Exercícios Propostos,
Submeter Resolução, página pública da resolução e avaliação), para que o
estudante sempre veja o circuito logo abaixo do enunciado.
"""

from __future__ import annotations

import base64
import re

import streamlit as st

from ..errors import AppError
from ..services import Platform
from ..services.exercises import Exercise, Figure
from .runtime import get_platform
from .widgets import esc, md


def statement_md(text: str) -> str:
    """Preserva as quebras de linha do enunciado (itens a), b), c)…) no Markdown."""
    return re.sub(r"(?<!\n)\n(?!\n)", "  \n", (text or "").strip())


@st.cache_data(show_spinner=False, max_entries=400, ttl=3600)
def _figure_bytes(fig_id: str, source: str, ref: str) -> bytes:
    p = get_platform()
    fig = Figure(id=fig_id, exercise_id="", position=0, source=source, ref=ref, label="", caption="", width=None, height=None)
    return p.exercises.figure_bytes(fig)


@st.cache_data(show_spinner=False, ttl=60, max_entries=500)
def _figures_for(exercise_id: str) -> list[Figure]:
    return get_platform().exercises.figures(exercise_id)


def clear_figure_cache() -> None:
    _figures_for.clear()
    _figure_bytes.clear()


@st.dialog("Figura do circuito", width="large")
def _zoom(data: bytes, title: str) -> None:
    if title:
        st.markdown(f"**{title}**")
    mime = "image/jpeg" if data[:3] == b"\xff\xd8\xff" else "image/png"
    b64 = base64.b64encode(data).decode("ascii")
    # Imagem ampliada (1,5×) dentro de um painel rolável: no celular, deslize para percorrer o circuito.
    st.markdown(
        f'<div class="ex-fig-zoom" tabindex="0" aria-label="Figura ampliada; role para ver todo o circuito">'
        f'<img src="data:{mime};base64,{b64}" alt="{esc(title or "Figura do circuito")}"></div>',
        unsafe_allow_html=True,
    )
    st.caption("Figura ampliada. No celular, deslize dentro do quadro para percorrer o circuito; "
               "a pinça do navegador também funciona.")


def render_figures(exercise_id: str, *, key: str) -> None:
    for fig in _figures_for(exercise_id):
        with st.container(key=f"ex-fig-{key}-{fig.id}"):
            try:
                data = _figure_bytes(fig.id, fig.source, fig.ref)
            except AppError as exc:
                st.warning(f"{fig.label or 'Figura'} indisponível no momento. {exc.message}")
                continue
            # Largura natural (sem ampliar a imagem e borrar os valores); no celular o CSS limita a 100%.
            st.image(data, width=int(min(fig.width or 720, 820)))
            title = " · ".join(x for x in (fig.label, fig.caption) if x)
            c1, c2 = st.columns([4, 1.3], vertical_alignment="center")
            if title:
                c1.markdown(f'<div class="ex-fig__caption">{esc(title)}</div>', unsafe_allow_html=True)
            if c2.button("Ampliar figura", key=f"zoom-{key}-{fig.id}", icon=":material/zoom_in:", use_container_width=True):
                _zoom(data, title)


def render_exercise(p: Platform, ex: Exercise, *, key: str, show_statement_label: bool = True) -> None:
    if show_statement_label:
        md('<div class="ex-panel__label">Enunciado</div>')
    st.markdown(statement_md(ex.statement))
    render_figures(ex.id, key=key)
    if ex.description:
        md('<div class="ex-panel__label ex-panel__label--spaced">Descrição complementar</div>')
        st.markdown(statement_md(ex.description))
    if ex.support_material:
        md('<div class="ex-panel__label ex-panel__label--spaced">Materiais de apoio</div>')
        st.markdown(statement_md(ex.support_material))
