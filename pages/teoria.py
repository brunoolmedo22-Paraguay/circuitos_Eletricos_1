"""Módulo: Aprenda a Teoria — consulta teórica baseada no livro de Boylestad."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from utils import SECTIONS, configure_page, data_uri, load_global_style, render_html, render_sidebar
from utils.teoria import (
    by_chapter,
    by_topic,
    chapters,
    formulas_for,
    frequent_theories,
    metadata,
    search_theories,
    topics,
)

configure_page(subtitle="Aprenda a Teoria")
load_global_style()

_page_css = Path(__file__).resolve().parent.parent / "styles" / "teoria.css"
if _page_css.exists():
    st.markdown(f"<style>{_page_css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

render_sidebar(active="teoria")

sec = next(s for s in SECTIONS if s["key"] == "teoria")
icon_uri = data_uri(sec["image"])
meta = metadata()

render_html(
    f"""
    <div class="page-hero theory-page-hero">
      <div class="page-hero__badge">
        {f'<img src="{icon_uri}" alt="" />' if icon_uri else sec['icon']}
      </div>
      <div class="page-hero__text">
        <span class="eyebrow">Módulo</span>
        <h1>{sec['title']}</h1>
        <p>{sec['description']}</p>
      </div>
    </div>
    """
)

if "theory_nav" not in st.session_state:
    st.session_state.theory_nav = "Teorias frequentes"


def set_mode(mode_name: str) -> None:
    st.session_state.theory_nav = mode_name


def render_theory_card(item: dict) -> None:
    """Renderiza um cartão curto: conceito, definição, fórmulas e referência."""
    # Título, rótulo e definição ficam no mesmo bloco HTML para preservar
    # o espaçamento interno mesmo com o gap global do Streamlit zerado.
    st.markdown(
        f"""
        <div class="theory-card-intro">
          <div class="theory-card-title">{item['title']}</div>
          <div class="theory-card-kicker theory-card-kicker--definition">DEFINIÇÃO</div>
          <div class="theory-card-summary">{item['summary']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    equations = formulas_for(item, limit=2)
    if equations:
        st.markdown("<div class='theory-card-kicker'>RELAÇÕES-CHAVE</div>", unsafe_allow_html=True)
        for formula in equations:
            st.latex(formula["latex"])

    st.markdown(
        f"""
        <div class="theory-card-reference">
          <span>REFERÊNCIA</span>
          <strong>Boylestad · 12ª ed.</strong><br>
          Cap. {item['chapter']:02d} · § {item['section']} · p. {item['pages']}
        </div>
        """,
        unsafe_allow_html=True,
    )


nav_col, viewer_col = st.columns([1.28, 5.72], gap="medium")

with nav_col:
    with st.container(border=True, key="theory-nav-panel"):
        st.markdown("<div class='theory-nav-heading'>TEORIA</div>", unsafe_allow_html=True)
        mode = st.session_state.theory_nav
        nav_items = [
            ("Teorias frequentes", "★  Mais frequentes"),
            ("Busca", "⌕  Busca"),
            ("Por capítulo", "▤  Por capítulo"),
            ("Por tema", "◫  Por tema"),
        ]
        for mode_name, label in nav_items:
            st.button(
                label,
                key=f"theory_nav_{mode_name}",
                type="primary" if mode == mode_name else "secondary",
                use_container_width=True,
                on_click=set_mode,
                args=(mode_name,),
            )

        st.markdown("<div class='theory-nav-divider'></div>", unsafe_allow_html=True)

        if mode == "Busca":
            query = st.text_input(
                "Buscar conceito",
                placeholder="Ex.: potência, resistência, Thévenin, fasores…",
                key="theory_search",
            )
            st.caption("Busque por conceito, tema, capítulo ou palavra-chave.")

        elif mode == "Por capítulo":
            chapter_rows = chapters()
            labels = {
                f"Cap. {c['number']:02d} · {c['title']}": c["number"]
                for c in chapter_rows
            }
            selected_label = st.selectbox(
                "Capítulo",
                list(labels.keys()),
                index=3,
                key="theory_chapter",
            )

        elif mode == "Por tema":
            all_topics = topics()
            preferred = "Potência" if "Potência" in all_topics else all_topics[0]
            selected_topic = st.selectbox(
                "Tema",
                all_topics,
                index=all_topics.index(preferred),
                key="theory_topic",
            )

        else:
            st.caption("Conceitos essenciais do livro reunidos em cartões curtos de consulta.")

        st.markdown(
            f"<div class='theory-db-note'><strong>{meta['theory_count']}</strong> conceitos · "
            f"<strong>{meta['chapter_count']}</strong> capítulos</div>",
            unsafe_allow_html=True,
        )

with viewer_col:
    if mode == "Teorias frequentes":
        rows = frequent_theories(limit=24)
        title = "Teorias mais frequentes"
        subtitle = ""
    elif mode == "Busca":
        query = st.session_state.get("theory_search", "")
        rows = search_theories(query, limit=60)
        title = "Resultados da busca" if query else "Busca de conceitos"
        subtitle = (
            f"{len(rows)} resultado(s) para “{query}”"
            if query
            else "Digite um conceito; enquanto isso, são exibidas as teorias mais frequentes."
        )
    elif mode == "Por capítulo":
        chapter_number = labels[selected_label]
        rows = by_chapter(chapter_number)
        title = selected_label
        subtitle = f"{len(rows)} conceito(s) resumido(s) neste capítulo"
    else:
        rows = by_topic(selected_topic)
        title = selected_topic
        subtitle = f"{len(rows)} conceito(s) relacionado(s) a este tema"

    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="theory-view-head">
          <div>
            <div class="theory-view-kicker">CONSULTA</div>
            <h2>{title}</h2>
            {subtitle_html}
          </div>
          <div class="theory-view-count">{len(rows)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not rows:
        st.info("Nenhum conceito foi encontrado com esse critério. Tente outra palavra, capítulo ou tema.")
    else:
        # Grade em linhas reais (3 cartões por linha). Evita o efeito de
        # "masonry" das três colunas permanentes, no qual cartões de alturas
        # diferentes ficavam visualmente colados ou desalinhados.
        for row_start in range(0, len(rows), 3):
            row_items = rows[row_start:row_start + 3]
            grid = st.columns(3, gap="large")
            for col, item in zip(grid, row_items):
                with col:
                    with st.container(key=f"theory-card-{item['id']}"):
                        render_theory_card(item)
            st.markdown("<div class='theory-row-spacer'></div>", unsafe_allow_html=True)

st.page_link("app.py", label="Voltar ao início", icon=":material/arrow_back:")
