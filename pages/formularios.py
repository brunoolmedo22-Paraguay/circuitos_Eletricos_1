"""Módulo: Formulários — catálogo interativo de equações."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from utils import SECTIONS, configure_page, data_uri, load_global_style, render_html, render_sidebar
from utils.formulas import (
    by_chapter,
    by_topic,
    chapters,
    frequent_formulas,
    metadata,
    related_formulas,
    search_formulas,
    topics,
)

configure_page(subtitle="Formulários")
load_global_style()

# CSS exclusivo desta página: não altera Interaja, Teoria nem Exercícios.
_page_css = Path(__file__).resolve().parent.parent / "styles" / "formularios.css"
if _page_css.exists():
    st.markdown(f"<style>{_page_css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

render_sidebar(active="formularios")

sec = next(s for s in SECTIONS if s["key"] == "formularios")
icon_uri = data_uri(sec["image"])
meta = metadata()

render_html(
    f"""
    <div class="page-hero formula-page-hero">
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

# Estado local desta página.
if "formula_selected_id" not in st.session_state:
    st.session_state.formula_selected_id = None
if "formula_nav" not in st.session_state:
    st.session_state.formula_nav = "Fórmulas frequentes"


def toggle_formula(formula_id: str) -> None:
    """Abre/fecha os detalhes dentro do próprio cartão da fórmula."""
    current = st.session_state.get("formula_selected_id")
    st.session_state.formula_selected_id = None if current == formula_id else formula_id


def set_mode(mode_name: str) -> None:
    st.session_state.formula_nav = mode_name
    # Os detalhes pertencem ao contexto da grade visível. Ao mudar de
    # consulta, evitamos manter um cartão "aberto" fora da tela.
    st.session_state.formula_selected_id = None


def render_inline_details(formula: dict) -> None:
    """Renderiza os detalhes dentro do painel da fórmula selecionada."""
    st.markdown("<div class='formula-card-detail-kicker'>DETALHES</div>", unsafe_allow_html=True)

    if formula.get("variables"):
        st.markdown("**Variáveis**")
        for symbol, meaning in formula["variables"].items():
            st.markdown(f"- ${symbol}$ — {meaning}")

    if formula.get("variants"):
        st.markdown("**Variantes**")
        for variant in formula["variants"][:4]:
            st.latex(variant)

    if formula.get("note"):
        st.markdown("**Nota**")
        st.caption(formula["note"])

    st.markdown("**Temas**")
    st.caption(" · ".join(formula.get("topics", [])))

    st.markdown("**Referência**")
    st.caption(
        f"Boylestad · 12ª ed. · Cap. {formula['chapter']} · "
        f"Seção {formula['section']} · p. {formula['pages']}"
    )

    related = related_formulas(formula, limit=4)
    if related:
        st.markdown("**Relacionadas**")
        st.caption(" · ".join(item["name"] for item in related))


nav_col, viewer_col = st.columns([1.28, 5.72], gap="medium")

with nav_col:
    with st.container(border=True, key="formula-nav-panel"):
        st.markdown("<div class='formula-nav-heading'>FORMULÁRIO</div>", unsafe_allow_html=True)
        mode = st.session_state.formula_nav
        nav_items = [
            ("Fórmulas frequentes", "★  Mais frequentes"),
            ("Busca", "⌕  Busca"),
            ("Por capítulo", "▤  Por capítulo"),
            ("Por tema", "◫  Por tema"),
        ]
        for mode_name, label in nav_items:
            st.button(
                label,
                key=f"nav_{mode_name}",
                type="primary" if mode == mode_name else "secondary",
                use_container_width=True,
                on_click=set_mode,
                args=(mode_name,),
            )
        st.markdown("<div class='formula-nav-divider'></div>", unsafe_allow_html=True)

        if mode == "Busca":
            query = st.text_input(
                "Buscar fórmula",
                placeholder="Ex.: potência, corrente, Thévenin, RC…",
                key="formula_search",
            )
            st.caption("Busque por nome, variável, tema, alias ou conceito.")

        elif mode == "Por capítulo":
            chapter_rows = chapters()
            labels = {
                f"Cap. {c['number']:02d} · {c['title']}": c["number"]
                for c in chapter_rows
            }
            selected_label = st.selectbox(
                "Capítulo",
                list(labels.keys()),
                index=3,  # Cap. 4: Ohm, potência e energia
                key="formula_chapter",
            )

        elif mode == "Por tema":
            all_topics = topics()
            default_topic = "Potência" if "Potência" in all_topics else all_topics[0]
            selected_topic = st.selectbox(
                "Tema",
                all_topics,
                index=all_topics.index(default_topic),
                key="formula_topic",
            )

        else:
            st.caption("As relações mais utilizadas na resolução de circuitos, reunidas em uma única visualização.")

        st.markdown(
            f"<div class='formula-db-note'><strong>{meta['formula_count']}</strong> fórmulas · "
            f"<strong>{meta['chapter_count']}</strong> capítulos</div>",
            unsafe_allow_html=True,
        )

with viewer_col:
    if mode == "Fórmulas frequentes":
        rows = frequent_formulas(limit=24)
        title = "Fórmulas mais frequentes"
        subtitle = "Consulta rápida · CC, redes, transitórios e fundamentos de CA"
    elif mode == "Busca":
        query = st.session_state.get("formula_search", "")
        rows = search_formulas(query, limit=60)
        title = "Resultados da busca" if query else "Busca de fórmulas"
        subtitle = f"{len(rows)} resultado(s) para “{query}”" if query else "Digite um conceito; enquanto isso, são exibidas fórmulas frequentes."
    elif mode == "Por capítulo":
        chapter_number = labels[selected_label]
        rows = by_chapter(chapter_number)
        title = selected_label
        subtitle = f"{len(rows)} fórmula(s) indexada(s) neste capítulo"
    else:
        rows = by_topic(selected_topic)
        title = selected_topic
        subtitle = f"{len(rows)} fórmula(s) relacionadas a este tema"

    st.markdown(
        f"""
        <div class="formula-view-head">
          <div>
            <div class="formula-view-kicker">CONSULTA</div>
            <h2>{title}</h2>
            <p>{subtitle}</p>
          </div>
          <div class="formula-view-count">{len(rows)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not rows:
        st.info("Nenhuma fórmula foi encontrada com esse critério. Tente outra palavra ou tema.")
    else:
        # Três colunas densas: o objetivo é visualizar muitas fórmulas ao mesmo tempo.
        grid = st.columns(3, gap="medium")
        for idx, formula in enumerate(rows):
            is_open = st.session_state.formula_selected_id == formula["id"]
            card_state = "open" if is_open else "closed"
            card_key = f"formula-card-{card_state}-{formula['id']}"

            with grid[idx % 3]:
                # O key do container vira uma classe CSS estável (st-key-...).
                # Assim o visual do painel não depende dos data-testid internos
                # do Streamlit, que podem variar entre versões.
                with st.container(key=card_key):
                    st.markdown(f"<div class='formula-card-name'>{formula['name']}</div>", unsafe_allow_html=True)
                    st.latex(formula["latex"])
                    st.caption(
                        f"Cap. {formula['chapter']:02d} · § {formula['section']} · p. {formula['pages']}"
                    )
                    st.button(
                        "Ocultar detalhes" if is_open else "Ver detalhes",
                        key=f"formula_{mode}_{formula['id']}",
                        on_click=toggle_formula,
                        args=(formula["id"],),
                        use_container_width=True,
                    )

                    if is_open:
                        # O detalhe nasce dentro do próprio card. O container
                        # keyed permite animar a abertura via CSS sem JavaScript.
                        with st.container(key=f"formula-detail-{formula['id']}"):
                            render_inline_details(formula)

st.page_link("app.py", label="Voltar ao início", icon=":material/arrow_back:")
