"""Módulo: Interaja com a Teoria — microexperimentos didáticos."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from components.experiments import render_experiment
from utils import SECTIONS, configure_page, data_uri, load_global_style, render_html, render_sidebar

configure_page(subtitle="Interaja com a Teoria")
load_global_style()

_page_css = Path(__file__).resolve().parent.parent / "styles" / "interaja.css"
if _page_css.exists():
    st.markdown(f"<style>{_page_css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

render_sidebar(active="interaja")

sec = next(s for s in SECTIONS if s["key"] == "interaja")
icon_uri = data_uri(sec["image"])

render_html(
    f"""
    <div class="page-hero interact-page-hero">
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

if "interact_experiment" not in st.session_state:
    st.session_state.interact_experiment = None


def open_experiment(experiment: str) -> None:
    st.session_state.interact_experiment = experiment


def close_experiment() -> None:
    st.session_state.interact_experiment = None


if st.session_state.interact_experiment in {"ohm", "sources_dc", "resistors", "resistor_colors", "voltage_divider", "kcl", "joule_power"}:
    with st.container(key="interact-back"):
        st.button("← Voltar aos experimentos", on_click=close_experiment)

    # Os microexperimentos são autocontidos: a interação acontece no
    # navegador, sem rerun do Streamlit a cada ajuste do aluno.
    if st.session_state.interact_experiment == "ohm":
        render_experiment("ohm", height=820)
    elif st.session_state.interact_experiment == "sources_dc":
        render_experiment("sources_dc", height=900)
    elif st.session_state.interact_experiment == "resistors":
        render_experiment("resistors", height=980)
    elif st.session_state.interact_experiment == "resistor_colors":
        render_experiment("resistor_colors", height=940)
    elif st.session_state.interact_experiment == "voltage_divider":
        render_experiment("voltage_divider", height=900)
    elif st.session_state.interact_experiment == "kcl":
        render_experiment("kcl", height=950)
    else:
        render_experiment("joule_power", height=1010)

else:
    st.markdown(
        """
        <div class="interact-view-head">
          <div>
            <div class="interact-view-kicker">MICROEXPERIMENTOS</div>
            <h2>Ver · mexer · perceber · testar</h2>
            <p>Experiências curtas para compreender o comportamento dos circuitos diretamente pela interação.</p>
          </div>
          <div class="interact-view-count">7</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    grid = st.columns(3, gap="small")
    with grid[0]:
        with st.container(key="interact-card-ohm"):
            st.markdown("<div class='interact-card-tag'>CC · FUNDAMENTOS</div>", unsafe_allow_html=True)
            st.markdown("<div class='interact-card-title'>Lei de Ohm</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='interact-card-summary'>Explore como tensão, corrente e resistência se relacionam em um circuito CC simples.</div>",
                unsafe_allow_html=True,
            )
            st.button(
                "Experimentar",
                key="open_ohm_experiment",
                use_container_width=True,
                on_click=open_experiment,
                args=("ohm",),
            )

    with grid[1]:
        with st.container(key="interact-card-sources-dc"):
            st.markdown("<div class='interact-card-tag'>CC · FONTES</div>", unsafe_allow_html=True)
            st.markdown("<div class='interact-card-title'>Fontes CC</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='interact-card-summary'>Monte fontes em série ou em paralelo e observe como a tensão e a capacidade resultantes se modificam.</div>",
                unsafe_allow_html=True,
            )
            st.button(
                "Experimentar",
                key="open_sources_dc_experiment",
                use_container_width=True,
                on_click=open_experiment,
                args=("sources_dc",),
            )

    with grid[2]:
        with st.container(key="interact-card-resistors"):
            st.markdown("<div class='interact-card-tag'>CC · RESISTORES</div>", unsafe_allow_html=True)
            st.markdown("<div class='interact-card-title'>Resistores em Série e Paralelo</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='interact-card-summary'>Monte associações de resistores e observe como a resistência equivalente se modifica.</div>",
                unsafe_allow_html=True,
            )
            st.button(
                "Experimentar",
                key="open_resistors_experiment",
                use_container_width=True,
                on_click=open_experiment,
                args=("resistors",),
            )

    second_row = st.columns(3, gap="small")
    with second_row[0]:
        with st.container(key="interact-card-resistor-colors"):
            st.markdown("<div class='interact-card-tag'>CC · RESISTORES</div>", unsafe_allow_html=True)
            st.markdown("<div class='interact-card-title'>Código de Cores</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='interact-card-summary'>Altere as faixas de um resistor e descubra instantaneamente seu valor e tolerância.</div>",
                unsafe_allow_html=True,
            )
            st.button(
                "Experimentar",
                key="open_resistor_colors_experiment",
                use_container_width=True,
                on_click=open_experiment,
                args=("resistor_colors",),
            )

    with second_row[1]:
        with st.container(key="interact-card-voltage-divider"):
            st.markdown("<div class='interact-card-tag'>CC · TENSÃO</div>", unsafe_allow_html=True)
            st.markdown("<div class='interact-card-title'>Divisor de Tensão</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='interact-card-summary'>Defina a fonte e os resistores e observe como a tensão se distribui pelo circuito.</div>",
                unsafe_allow_html=True,
            )
            st.button(
                "Experimentar",
                key="open_voltage_divider_experiment",
                use_container_width=True,
                on_click=open_experiment,
                args=("voltage_divider",),
            )

    with second_row[2]:
        with st.container(key="interact-card-kcl"):
            st.markdown("<div class='interact-card-tag'>CC · CORRENTE</div>", unsafe_allow_html=True)
            st.markdown("<div class='interact-card-title'>KCL e Divisão de Corrente</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='interact-card-summary'>Observe a corrente chegar a um nó, dividir-se entre os ramos e recombinar-se no circuito.</div>",
                unsafe_allow_html=True,
            )
            st.button(
                "Experimentar",
                key="open_kcl_experiment",
                use_container_width=True,
                on_click=open_experiment,
                args=("kcl",),
            )


    third_row = st.columns(3, gap="small")
    with third_row[0]:
        with st.container(key="interact-card-joule-power"):
            st.markdown("<div class='interact-card-tag'>CC · POTÊNCIA</div>", unsafe_allow_html=True)
            st.markdown("<div class='interact-card-title'>Potência e Efeito Joule</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='interact-card-summary'>Energize diferentes cargas resistivas e observe como a potência elétrica se transforma em calor.</div>",
                unsafe_allow_html=True,
            )
            st.button(
                "Experimentar",
                key="open_joule_power_experiment",
                use_container_width=True,
                on_click=open_experiment,
                args=("joule_power",),
            )

    st.page_link("app.py", label="Voltar ao início", icon=":material/arrow_back:")
