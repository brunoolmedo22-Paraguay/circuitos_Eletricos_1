"""Módulo: Formularios — catálogo interactivo de ecuaciones."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from utils import SECTIONS, configure_page, data_uri, load_global_style, render_html, render_sidebar
from utils.formulas import (
    by_chapter,
    by_topic,
    chapters,
    frequent_formulas,
    get_formula,
    metadata,
    related_formulas,
    search_formulas,
    topics,
)

configure_page(subtitle="Formularios")
load_global_style()

# CSS exclusivo de esta página: no altera Interactúe, Teoría ni Ejercicios.
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

# Estado local de esta página.
if "formula_selected_id" not in st.session_state:
    st.session_state.formula_selected_id = None
if "formula_nav" not in st.session_state:
    st.session_state.formula_nav = "Fórmulas frecuentes"


def select_formula(formula_id: str) -> None:
    st.session_state.formula_selected_id = formula_id


def clear_formula() -> None:
    st.session_state.formula_selected_id = None


def set_mode(mode_name: str) -> None:
    st.session_state.formula_nav = mode_name


nav_col, viewer_col = st.columns([1.28, 5.72], gap="medium")

with nav_col:
    with st.container(border=True):
        st.markdown("<div class='formula-nav-heading'>FORMULARIO</div>", unsafe_allow_html=True)
        mode = st.session_state.formula_nav
        nav_items = [
            ("Fórmulas frecuentes", "★  Más frecuentes"),
            ("Buscador", "⌕  Buscador"),
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

        if mode == "Buscador":
            query = st.text_input(
                "Buscar fórmula",
                placeholder="Ej.: potencia, corriente, Thévenin, RC…",
                key="formula_search",
            )
            st.caption("Busca por nombre, variable, tema, alias o concepto.")

        elif mode == "Por capítulo":
            chapter_rows = chapters()
            labels = {
                f"Cap. {c['number']:02d} · {c['title']}": c["number"]
                for c in chapter_rows
            }
            selected_label = st.selectbox(
                "Capítulo",
                list(labels.keys()),
                index=3,  # Cap. 4: Ohm, potencia y energía
                key="formula_chapter",
            )

        elif mode == "Por tema":
            all_topics = topics()
            default_topic = "Potencia" if "Potencia" in all_topics else all_topics[0]
            selected_topic = st.selectbox(
                "Tema",
                all_topics,
                index=all_topics.index(default_topic),
                key="formula_topic",
            )

        else:
            st.caption("Las relaciones que más se usan al resolver circuitos, reunidas en una sola vista.")

        st.markdown(
            f"<div class='formula-db-note'><strong>{meta['formula_count']}</strong> fórmulas · "
            f"<strong>{meta['chapter_count']}</strong> capítulos</div>",
            unsafe_allow_html=True,
        )

with viewer_col:
    if mode == "Fórmulas frecuentes":
        rows = frequent_formulas(limit=24)
        title = "Fórmulas más frecuentes"
        subtitle = "Consulta rápida · CC, redes, transitorios y fundamentos de CA"
    elif mode == "Buscador":
        query = st.session_state.get("formula_search", "")
        rows = search_formulas(query, limit=60)
        title = "Resultados de búsqueda" if query else "Buscador de fórmulas"
        subtitle = f"{len(rows)} resultado(s) para “{query}”" if query else "Escribe un concepto; mientras tanto se muestran fórmulas frecuentes."
    elif mode == "Por capítulo":
        chapter_number = labels[selected_label]
        rows = by_chapter(chapter_number)
        title = selected_label
        subtitle = f"{len(rows)} fórmula(s) indexada(s) en este capítulo"
    else:
        rows = by_topic(selected_topic)
        title = selected_topic
        subtitle = f"{len(rows)} fórmula(s) relacionadas con este tema"

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

    selected = get_formula(st.session_state.formula_selected_id)
    if selected:
        with st.container(border=True):
            top_a, top_b = st.columns([5.4, 1.0], vertical_alignment="center")
            with top_a:
                st.markdown(f"### {selected['name']}")
                st.caption(
                    f"Cap. {selected['chapter']:02d} · Sección {selected['section']} · p. {selected['pages']}"
                )
            with top_b:
                st.button("Cerrar", key="formula_close", on_click=clear_formula, use_container_width=True)

            eq_col, info_col = st.columns([1.7, 2.3], gap="large")
            with eq_col:
                st.latex(selected["latex"])
                if selected.get("variants"):
                    st.markdown("**Variantes**")
                    for variant in selected["variants"][:4]:
                        st.latex(variant)
            with info_col:
                if selected.get("variables"):
                    st.markdown("**Variables**")
                    for symbol, meaning in selected["variables"].items():
                        st.markdown(f"- `${symbol}$` — {meaning}")
                st.markdown("**Temas**")
                st.caption(" · ".join(selected.get("topics", [])))
                st.markdown("**Referencia**")
                st.caption(
                    f"Boylestad · 12ª ed. · Cap. {selected['chapter']} · "
                    f"Sección {selected['section']} · p. {selected['pages']}"
                )
                related = related_formulas(selected, limit=4)
                if related:
                    st.markdown("**Relacionadas**")
                    st.caption(" · ".join(item["name"] for item in related))

        st.markdown("<div class='formula-after-detail'></div>", unsafe_allow_html=True)

    if not rows:
        st.info("No encontré fórmulas con ese criterio. Prueba con otra palabra o tema.")
    else:
        # Tres columnas densas: el objetivo es ver muchas fórmulas a la vez.
        grid = st.columns(3, gap="medium")
        for idx, formula in enumerate(rows):
            with grid[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"<div class='formula-card-name'>{formula['name']}</div>", unsafe_allow_html=True)
                    st.latex(formula["latex"])
                    st.caption(
                        f"Cap. {formula['chapter']:02d} · § {formula['section']} · p. {formula['pages']}"
                    )
                    st.button(
                        "Ver detalles",
                        key=f"formula_{mode}_{formula['id']}",
                        on_click=select_formula,
                        args=(formula["id"],),
                        use_container_width=True,
                    )

st.page_link("app.py", label="Volver al inicio", icon=":material/arrow_back:")
