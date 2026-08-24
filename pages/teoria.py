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
if "theory_selected_id" not in st.session_state:
    st.session_state.theory_selected_id = None


def toggle_theory(theory_id: str) -> None:
    """Abre/fecha os detalhes dentro do próprio painel conceitual."""
    current = st.session_state.get("theory_selected_id")
    st.session_state.theory_selected_id = None if current == theory_id else theory_id


def set_mode(mode_name: str) -> None:
    st.session_state.theory_nav = mode_name
    # O painel aberto pertence à grade atual; ao trocar a consulta, fechamos
    # o detalhe para evitar manter um conceito aberto fora da nova seleção.
    st.session_state.theory_selected_id = None


def render_theory_intro(item: dict) -> None:
    """Conteúdo sempre visível: somente título e definição curta."""
    st.markdown(
        f"""
        <div class="theory-card-intro">
          <div class="theory-card-title">{item['title']}</div>
          <div class="theory-card-summary">{item['summary']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_theory_details(item: dict) -> None:
    """Conteúdo revelado dentro do próprio painel ao clicar em Ver mais."""
    st.markdown("<div class='theory-detail-kicker'>DETALHES</div>", unsafe_allow_html=True)

    equations = formulas_for(item, limit=2)
    if equations:
        st.markdown("<div class='theory-card-kicker'>RELAÇÕES-CHAVE</div>", unsafe_allow_html=True)
        for formula in equations:
            st.latex(formula["latex"])

    item_topics = item.get("topics", [])
    if item_topics:
        st.markdown("<div class='theory-card-kicker theory-card-kicker--topics'>TEMAS</div>", unsafe_allow_html=True)
        st.caption(" · ".join(item_topics))

    st.markdown(
        f"""
        <div class="theory-card-reference">
          <span>ONDE ENCONTRAR</span>
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
        # Mantemos três colunas permanentes, exatamente como em Formulários.
        # Assim, quando um cartão expande, ele só empurra os cartões da sua
        # própria coluna, sem interferir nas colunas vizinhas.
        grid = st.columns(3, gap="medium")
        for idx, item in enumerate(rows):
            is_open = st.session_state.theory_selected_id == item["id"]
            card_state = "open" if is_open else "closed"

            with grid[idx % 3]:
                with st.container(key=f"theory-card-{card_state}-{item['id']}"):
                    render_theory_intro(item)
                    st.button(
                        "Ocultar detalhes" if is_open else "Ver mais",
                        key=f"theory_toggle_{mode}_{item['id']}",
                        on_click=toggle_theory,
                        args=(item["id"],),
                        use_container_width=True,
                    )

                    if is_open:
                        with st.container(key=f"theory-detail-{item['id']}"):
                            render_theory_details(item)

st.page_link("app.py", label="Voltar ao início", icon=":material/arrow_back:")
