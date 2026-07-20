"""Repositorio de consulta del módulo ``Aprenda la Teoría``.

Versión 0.3: artículos técnicos breves, búsqueda, referencias bibliográficas y
herramientas de consulta. La página complementa las clases; no intenta
reemplazarlas con un curso autónomo.
"""

from __future__ import annotations

from html import escape
import unicodedata
from urllib.parse import quote

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from utils import configure_page, load_global_style, render_html
from utils.theory import (
    THEORY_UNITS,
    TheoryTopic,
    TheoryUnit,
    engineering_notation,
    get_topic,
    get_unit,
)


configure_page(subtitle="Aprenda la Teoría")
load_global_style()


PANEL = "#8b6a8f"
ACCENT = "#532458"
INK = "#211c26"
MUTED = "#6b6472"
GREEN = "#2f7d63"

PLOT_CONFIG = {"displayModeBar": False, "responsive": True, "scrollZoom": False}

SEARCH_ALIASES = {
    "que-es-un-circuito": "fuente carga conductor camino cerrado circuito simple batería",
    "tension-y-corriente": "voltaje potencial carga amperio coulomb flujo I Q t V W",
    "resistencia": "resistor ohm resistividad conductancia siemens colores rho longitud área",
    "ley-de-ohm": "V R I voltios amperios ohmios característica pendiente",
    "potencia-y-energia": "watt joule trabajo eficiencia rendimiento P W eta",
    "consumo-electrico": "kwh wh tarifa factura costo energía potencia nominal",
    "abierto-corto-medicion": "cortocircuito multímetro amperímetro voltímetro serie paralelo",
}


def _query_value(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(character for character in text if not unicodedata.combining(character))


def _style_figure(
    figure: go.Figure,
    *,
    title: str,
    x_title: str,
    y_title: str,
    height: int = 390,
) -> go.Figure:
    figure.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        height=height,
        margin={"l": 58, "r": 28, "t": 72, "b": 56},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"family": "Inter, sans-serif", "color": INK, "size": 13},
        title_font={"family": "Poppins, sans-serif", "color": ACCENT, "size": 18},
        hoverlabel={"bgcolor": "#ffffff", "font_color": INK},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    figure.update_xaxes(title=x_title, showgrid=True, gridcolor="#eee9f0", zerolinecolor="#d8cedb", linecolor="#d8cedb")
    figure.update_yaxes(title=y_title, showgrid=True, gridcolor="#eee9f0", zerolinecolor="#d8cedb", linecolor="#d8cedb")
    return figure


def _plot(figure: go.Figure, key: str) -> None:
    st.plotly_chart(figure, width="stretch", config=PLOT_CONFIG, key=f"theory_plot_{key}")


def _section(anchor: str, label: str, title: str, text: str = "") -> None:
    render_html(
        f"""
        <div class="reference-section-title" id="{escape(anchor)}">
          <span>{escape(label)}</span>
          <div>
            <h2>{escape(title)}</h2>
            {f'<p>{escape(text)}</p>' if text else ''}
          </div>
        </div>
        """
    )


def _article_index(items: list[tuple[str, str]]) -> None:
    links = "".join(f'<a href="#{escape(anchor)}">{escape(label)}</a>' for anchor, label in items)
    render_html(
        f"""
        <nav class="article-index">
          <span>En este artículo</span>
          <div>{links}</div>
        </nav>
        """
    )


def _fact_sheet(rows: list[tuple[str, str]]) -> None:
    body = "".join(
        f'<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>' for label, value in rows
    )
    render_html(f'<dl class="fact-sheet">{body}</dl>')


def _reference_table(headers: list[str], rows: list[list[str]]) -> None:
    heading = "".join(f"<th>{escape(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    render_html(f'<div class="reference-table-wrap"><table class="reference-table"><thead><tr>{heading}</tr></thead><tbody>{body}</tbody></table></div>')


def _note(title: str, body: str, kind: str = "technical") -> None:
    render_html(
        f"""
        <aside class="reference-note reference-note--{escape(kind)}">
          <strong>{escape(title)}</strong>
          <p>{body}</p>
        </aside>
        """
    )


def _source_box(pages: str, sections: str) -> None:
    render_html(
        f"""
        <footer class="article-source">
          <span>Referencia utilizada</span>
          <p>BOYLESTAD, Robert L. <em>Introdução à análise de circuitos</em>.
          12. ed. São Paulo: Pearson Prentice Hall, 2012, {escape(pages)}.</p>
          <small>Secciones consultadas: {escape(sections)}. Contenido sintetizado y adaptado para consulta académica.</small>
        </footer>
        """
    )


def _render_topbar() -> None:
    render_html(
        """
        <div class="theory-page-marker" aria-hidden="true"></div>
        <nav class="theory-topbar">
          <a href="../" target="_self">← Inicio</a>
          <div><span>UNILA</span> · Monitoría de Circuitos Eléctricos I</div>
          <span class="theory-version">Versión 0.3</span>
        </nav>
        """
    )


def _topic_card(unit: TheoryUnit, topic: TheoryTopic, order: int) -> str:
    if topic.available:
        href = f"?unit={quote(unit.key)}&topic={quote(topic.key)}"
        source = f"Boylestad, 2012 · {topic.source_pages}"
        return f"""
        <a class="topic-card topic-card--ready" href="{href}" target="_self">
          <div class="topic-card__top"><span class="topic-card__order">{order:02d}</span><span class="topic-card__status topic-card__status--ready">Disponible</span></div>
          <div class="topic-card__icon">{topic.icon}</div>
          <h3>{escape(topic.title)}</h3>
          <p>{escape(topic.description)}</p>
          <div class="topic-card__source">{escape(source)}</div>
          <div class="topic-card__cta">Consultar <b>→</b></div>
        </a>
        """
    return f"""
    <article class="topic-card topic-card--locked">
      <div class="topic-card__top"><span class="topic-card__order">{order:02d}</span><span class="topic-card__status">Indexado</span></div>
      <div class="topic-card__icon">{topic.icon}</div>
      <h3>{escape(topic.title)}</h3>
      <p>{escape(topic.description)}</p>
      <div class="topic-card__cta">Contenido pendiente</div>
    </article>
    """


def _search_results(query: str) -> list[tuple[TheoryUnit, TheoryTopic, int]]:
    terms = [term for term in _normalize(query).split() if term]
    results: list[tuple[TheoryUnit, TheoryTopic, int]] = []
    for unit in THEORY_UNITS:
        for order, topic in enumerate(unit.topics, start=1):
            haystack = _normalize(
                " ".join(
                    [unit.title, topic.title, topic.description, SEARCH_ALIASES.get(topic.key, "")]
                )
            )
            if all(term in haystack for term in terms):
                results.append((unit, topic, order))
    return results


def _render_hub(unit: TheoryUnit) -> None:
    available_count = sum(topic.available for current in THEORY_UNITS for topic in current.topics)
    total_count = sum(len(current.topics) for current in THEORY_UNITS)
    render_html(
        f"""
        <header class="theory-hero theory-hero--reference">
          <div class="theory-hero__copy">
            <span class="eyebrow">Base de consulta de la disciplina</span>
            <h1>Aprenda la Teoría</h1>
            <p>Definiciones, ecuaciones, convenciones, casos particulares y herramientas
            para revisar rápidamente los contenidos trabajados en clase.</p>
            <div class="theory-hero__stats">
              <span><strong>7</strong> unidades</span>
              <span><strong>{available_count}</strong> artículos publicados</span>
              <span><strong>{total_count}</strong> entradas indexadas</span>
              <span><strong>Boylestad</strong> referencia principal</span>
            </div>
          </div>
          <div class="theory-hero__symbol" aria-hidden="true"><span>V</span><b>=</b><span>R</span><b>·</b><span>I</span></div>
        </header>
        """
    )

    _section("buscar", "Consulta", "Busque un concepto", "Localice una definición, magnitud, ecuación o método sin recorrer todo el material.")
    query = st.text_input(
        "Buscar en la base teórica",
        placeholder="Ej.: corriente, kWh, Ley de Ohm, supernodo…",
        label_visibility="collapsed",
        key="theory_search",
    )
    if query.strip():
        results = _search_results(query)
        render_html(f'<div class="search-summary"><strong>{len(results)}</strong> resultados para “{escape(query.strip())}”</div>')
        if results:
            cards = "".join(_topic_card(result_unit, topic, order) for result_unit, topic, order in results)
            render_html(f'<div class="topic-grid">{cards}</div>')
        else:
            st.info("No se encontraron coincidencias. Pruebe con otro término o seleccione una unidad.")
        return

    _section("unidades", "Índice", "Consulte por unidad", "La organización reproduce la secuencia de la disciplina y facilita volver a un tema específico.")
    unit_keys = [current.key for current in THEORY_UNITS]
    selected_key = st.selectbox(
        "Unidad temática",
        unit_keys,
        index=unit_keys.index(unit.key),
        format_func=lambda key: f"Unidad {get_unit(key).number} · {get_unit(key).title}",
    )
    if selected_key != unit.key:
        st.query_params["unit"] = selected_key
        if "topic" in st.query_params:
            del st.query_params["topic"]
        st.rerun()

    status = "Artículos disponibles" if any(topic.available for topic in unit.topics) else "Entradas indexadas"
    render_html(
        f"""
        <section class="unit-intro">
          <div class="unit-intro__number">{unit.number:02d}</div>
          <div class="unit-intro__copy">
            <div><span class="unit-status">{status}</span><span class="unit-reference">{escape(unit.reference)}</span></div>
            <h2>{escape(unit.title)}</h2><p>{escape(unit.description)}</p>
          </div>
        </section>
        """
    )
    cards = "".join(_topic_card(unit, topic, order) for order, topic in enumerate(unit.topics, start=1))
    render_html(f'<div class="topic-grid">{cards}</div>')

    roadmap = "".join(
        f"""
        <a class="roadmap-item {'roadmap-item--active' if item.key == unit.key else ''}" href="?unit={quote(item.key)}" target="_self">
          <span>{item.number:02d}</span><b>{escape(item.short_title)}</b><small>{escape(item.reference)}</small>
        </a>
        """
        for item in THEORY_UNITS
    )
    render_html(f'<div class="theory-roadmap">{roadmap}</div>')


def _render_article_header(unit: TheoryUnit, topic: TheoryTopic) -> None:
    render_html(
        f"""
        <div class="lesson-toolbar">
          <a href="?unit={quote(unit.key)}" target="_self">← Índice de la unidad</a>
          <span>Unidad {unit.number} · Repositorio teórico</span>
        </div>
        <header class="lesson-hero lesson-hero--reference">
          <div class="lesson-hero__icon">{topic.icon}</div>
          <div class="lesson-hero__copy">
            <span class="eyebrow">Artículo de referencia · {escape(unit.short_title)}</span>
            <h1>{escape(topic.title)}</h1>
            <p>{escape(topic.description)}</p>
            <div class="lesson-meta">
              <span>Boylestad, 2012 · {escape(topic.source_pages)}</span>
              <span>Consulta rápida</span>
              <span>Corriente continua</span>
            </div>
          </div>
        </header>
        """
    )


def _render_article_footer(unit: TheoryUnit, topic: TheoryTopic) -> None:
    position = unit.topics.index(topic)
    previous_topic = unit.topics[position - 1] if position > 0 else None
    next_topic = unit.topics[position + 1] if position + 1 < len(unit.topics) else None

    def card(item: TheoryTopic | None, direction: str) -> str:
        if item is None:
            return '<div class="lesson-nav-card lesson-nav-card--empty"></div>'
        label = "Artículo anterior" if direction == "previous" else "Artículo siguiente"
        arrow = "←" if direction == "previous" else "→"
        return f"""
        <a class="lesson-nav-card lesson-nav-card--{direction}" href="?unit={quote(unit.key)}&topic={quote(item.key)}" target="_self">
          <span>{arrow} {label}</span><strong>{escape(item.title)}</strong>
        </a>
        """

    render_html(f'<nav class="lesson-bottom-nav">{card(previous_topic, "previous")}{card(next_topic, "next")}</nav>')


def _simple_circuit_svg(voltage: float, resistance: float, closed: bool, current: float) -> str:
    switch = (
        '<line x1="335" y1="68" x2="395" y2="68" class="wire energized"/>'
        if closed
        else '<line x1="335" y1="68" x2="391" y2="36" class="switch-arm"/>'
    )
    current_label = engineering_notation(current, "A") if closed else "0 A"
    state = "CAMINO CERRADO" if closed else "CAMINO INTERRUMPIDO"
    state_class = "on" if closed else "off"
    energized = "energized" if closed else ""
    visible = "visible" if closed else ""
    return f"""
    <div class="circuit-visual circuit-visual--{state_class}">
      <div class="circuit-state">{state}</div>
      <svg viewBox="0 0 640 270" role="img" aria-label="Circuito simple con fuente, interruptor y resistor">
        <path d="M120 68 H305" class="wire {energized}"/><circle cx="320" cy="68" r="7" class="terminal"/>
        <circle cx="410" cy="68" r="7" class="terminal"/>{switch}<path d="M425 68 H520 V105" class="wire {energized}"/>
        <path d="M520 165 V215 H120 V168" class="wire {energized}"/><rect x="492" y="105" width="56" height="60" rx="8" class="resistor"/>
        <text x="520" y="135" class="svg-main" text-anchor="middle">R</text><text x="520" y="185" class="svg-small" text-anchor="middle">{resistance:.0f} Ω</text>
        <line x1="120" y1="105" x2="120" y2="132" class="battery-long"/><line x1="96" y1="142" x2="144" y2="142" class="battery-long"/>
        <line x1="104" y1="158" x2="136" y2="158" class="battery-short"/><text x="70" y="147" class="svg-main" text-anchor="middle">{voltage:.0f} V</text>
        <text x="365" y="28" class="svg-small" text-anchor="middle">Interruptor</text><path d="M235 49 h55" class="current-arrow {visible}"/>
        <polygon points="290,49 278,42 278,56" class="arrow-head {visible}"/><text x="262" y="35" class="svg-small" text-anchor="middle">I = {current_label}</text>
      </svg>
    </div>
    """


def _article_circuit() -> None:
    _article_index([("definicion", "Definición"), ("elementos", "Elementos"), ("estados", "Estados del circuito"), ("herramienta", "Herramienta")])
    _fact_sheet([("Objeto", "Circuito eléctrico"), ("Modelo mínimo", "Fuente + camino conductor + carga"), ("Condición para I ≠ 0", "Camino cerrado"), ("Variables básicas", "V, I y R")])

    _section("definicion", "Definición", "Circuito eléctrico")
    st.markdown(
        """
Un circuito eléctrico es una interconexión de elementos que establece una
trayectoria para la transferencia de carga y energía. En el circuito elemental
presentado por Boylestad, una batería, los conductores y una lámpara forman un
camino cerrado; al completar la conexión se establece un flujo dirigido de
carga. **(BOYLESTAD, 2012, p. 29).**

La tensión de la fuente es la condición que impulsa el sistema y la corriente es
la respuesta producida en la trayectoria disponible. **(BOYLESTAD, 2012,
pp. 28–30).**
"""
    )

    _section("elementos", "Estructura", "Elementos funcionales")
    _reference_table(
        ["Elemento", "Función en el modelo", "Ejemplos"],
        [
            ["Fuente", "Establece una diferencia de potencial", "Batería, generador, fuente CC"],
            ["Conexión", "Proporciona la trayectoria conductora", "Cable, pista, barra"],
            ["Carga", "Absorbe o convierte energía eléctrica", "Resistor, lámpara, motor"],
            ["Control", "Modifica la continuidad o configuración", "Interruptor, relé"],
            ["Protección", "Limita las consecuencias de una falla", "Fusible, disyuntor"],
        ],
    )

    _section("estados", "Consulta", "Estados básicos")
    _reference_table(
        ["Estado", "Trayectoria", "Corriente ideal", "Puede existir tensión"],
        [
            ["Cerrado", "Completa", "Determinada por la red", "Sí"],
            ["Abierto", "Interrumpida", "0 A", "Sí, entre los terminales abiertos"],
            ["Cortocircuito", "Muy baja resistencia", "Determinada por la red externa", "≈ 0 V sobre el corto"],
        ],
    )
    _note("Circuito abierto no significa circuito sin tensión", "La corriente de una rama abierta es nula, pero puede existir cualquier diferencia de potencial entre sus terminales. <span class='inline-citation'>(BOYLESTAD, 2012, pp. 179–180).</span>", "warning")

    _section("herramienta", "Herramienta", "Estado de un circuito simple", "Use el esquema para comprobar rápidamente el efecto de abrir la trayectoria.")
    with st.expander("Abrir herramienta de circuito", expanded=False):
        left, right = st.columns(2)
        with left:
            voltage = st.slider("Tensión de la fuente (V)", 1.0, 24.0, 12.0, 1.0, key="circuit_voltage")
            resistance = st.slider("Resistencia de la carga (Ω)", 10.0, 500.0, 120.0, 10.0, key="circuit_resistance")
        with right:
            closed = st.toggle("Interruptor cerrado", value=True, key="circuit_closed")
            current = voltage / resistance if closed else 0.0
            st.metric("Corriente", engineering_notation(current, "A"))
        render_html(_simple_circuit_svg(voltage, resistance, closed, current))
    _source_box("pp. 29–30 y 179–180", "2.4 Corrente; 6.8 Circuitos abertos e curtos-circuitos")


def _article_voltage_current() -> None:
    _article_index([("definiciones", "Definiciones"), ("relaciones", "Relaciones"), ("convenciones", "Convenciones"), ("herramienta", "Herramienta")])
    _fact_sheet([("Tensión", "V · voltio (V)"), ("Corriente", "I · amperio (A)"), ("Carga", "Q · coulomb (C)"), ("Energía", "W · joule (J)")])

    _section("definiciones", "Definiciones", "Tensión y corriente")
    st.markdown(
        """
La **tensión** entre dos puntos expresa la energía necesaria por unidad de carga
para desplazarla entre esos puntos. Un voltio equivale a un joule por coulomb.
**(BOYLESTAD, 2012, p. 27).**

La **corriente** cuantifica la carga que atraviesa una sección por unidad de
tiempo. Un amperio corresponde al paso de un coulomb por segundo.
**(BOYLESTAD, 2012, pp. 29–30).**
"""
    )
    equations = st.columns(2)
    equations[0].latex(r"V=\frac{W}{Q}\qquad [V]=\frac{J}{C}")
    equations[1].latex(r"I=\frac{Q}{t}\qquad [A]=\frac{C}{s}")

    _section("relaciones", "Relaciones", "Despejes y unidades")
    _reference_table(
        ["Magnitud buscada", "Relación", "Unidad SI"],
        [["Tensión", "V = W/Q", "voltio (V)"], ["Energía", "W = QV", "joule (J)"], ["Carga", "Q = W/V = It", "coulomb (C)"], ["Corriente media", "I = Q/t", "amperio (A)"], ["Tiempo", "t = Q/I", "segundo (s)"]],
    )

    _section("convenciones", "Convención", "Sentido de la corriente")
    st.markdown(
        """
En análisis de circuitos se adopta normalmente la **corriente convencional**,
orientada desde el potencial más alto hacia el más bajo en el circuito externo.
El movimiento de los electrones metálicos ocurre en sentido contrario. Boylestad
adopta explícitamente el sentido convencional para el desarrollo del libro.
**(BOYLESTAD, 2012, p. 30).**
"""
    )
    _note("Resultado negativo", "Una corriente calculada con signo negativo no invalida el análisis: indica que el sentido físico es opuesto a la referencia escogida.")

    _section("herramienta", "Herramienta", "Conversor carga–tiempo–corriente")
    with st.expander("Abrir calculadora I = Q/t", expanded=False):
        left, right = st.columns(2)
        with left:
            charge = st.slider("Carga transferida Q (C)", 0.5, 20.0, 6.0, 0.5, key="charge_q")
        with right:
            interval = st.slider("Intervalo Δt (s)", 0.5, 10.0, 3.0, 0.5, key="charge_t")
        current = charge / interval
        st.metric("Corriente media", engineering_notation(current, "A"))
        time = np.linspace(0, interval, 80)
        figure = go.Figure(go.Scatter(x=time, y=current * time, mode="lines", fill="tozeroy", line={"color": PANEL, "width": 4}, fillcolor="rgba(139,106,143,.16)", hovertemplate="t = %{x:.2f} s<br>Q = %{y:.2f} C<extra></extra>"))
        figure.add_trace(go.Scatter(x=[interval], y=[charge], mode="markers", marker={"size": 13, "color": ACCENT, "line": {"width": 3, "color": "white"}}, name="Valor consultado", hovertemplate="Δt = %{x:.2f} s<br>ΔQ = %{y:.2f} C<extra></extra>"))
        _plot(_style_figure(figure, title="Carga acumulada a corriente constante", x_title="Tiempo (s)", y_title="Carga (C)"), "charge_flow")
    _source_box("pp. 27–30", "2.3 Tensão; 2.4 Corrente")


def _article_resistance() -> None:
    _article_index([("definicion", "Definición"), ("dependencias", "Dependencias"), ("codigos", "Código de colores"), ("herramientas", "Herramientas")])
    _fact_sheet([("Magnitud", "Resistencia R"), ("Unidad", "ohmio (Ω)"), ("Inversa", "Conductancia G"), ("Unidad de G", "siemens (S)")])

    _section("definicion", "Definición", "Resistencia y conductancia")
    st.markdown(
        """
La **resistencia** representa la oposición que un material o elemento ofrece al
flujo de carga y se mide en ohmios. Boylestad relaciona esta oposición con las
interacciones de los electrones en la estructura del material.
**(BOYLESTAD, 2012, p. 51).**

La **conductancia** es la inversa de la resistencia y expresa la facilidad con
la que un material conduce corriente. **(BOYLESTAD, 2012, p. 67).**
"""
    )
    equations = st.columns(2)
    equations[0].latex(r"R=\rho\frac{L}{A}")
    equations[1].latex(r"G=\frac{1}{R}")

    _section("dependencias", "Relación", "Parámetros que determinan R")
    _reference_table(
        ["Parámetro", "Efecto manteniendo los demás constantes"],
        [["Resistividad ρ", "ρ mayor → R mayor"], ["Longitud L", "L mayor → R mayor"], ["Área A", "A mayor → R menor"], ["Temperatura", "En metales conductores, normalmente T mayor → R mayor"]],
    )
    _note("Alcance de R = ρL/A", "La resistividad depende de la temperatura; por ello, el valor de ρ utilizado debe corresponder a la condición térmica del conductor. <span class='inline-citation'>(BOYLESTAD, 2012, pp. 51–52).</span>")

    _section("codigos", "Identificación", "Código de cuatro bandas")
    _reference_table(
        ["Banda", "Información"],
        [["1.ª", "Primer dígito significativo"], ["2.ª", "Segundo dígito significativo"], ["3.ª", "Multiplicador en potencia de diez"], ["4.ª", "Tolerancia del fabricante"]],
    )
    st.markdown("El esquema de lectura de cuatro bandas y sus tolerancias se presenta en **Boylestad (2012, pp. 64–65)**.")

    _section("herramientas", "Herramientas", "Cálculo de conductor y decodificación")
    with st.expander("Calcular la resistencia de un conductor", expanded=False):
        materials = {"Cobre": 1.68e-8, "Aluminio": 2.82e-8, "Nicromo": 1.10e-6}
        c1, c2, c3 = st.columns(3)
        with c1:
            material = st.selectbox("Material", list(materials), key="wire_material")
        with c2:
            length = st.slider("Longitud (m)", 1.0, 100.0, 25.0, 1.0, key="wire_length")
        with c3:
            area = st.slider("Área (mm²)", 0.5, 10.0, 2.5, 0.5, key="wire_area")
        rho = materials[material]
        resistance = rho * length / (area * 1e-6)
        metrics = st.columns(2)
        metrics[0].metric("Resistencia", engineering_notation(resistance, "Ω"))
        metrics[1].metric("Conductancia", engineering_notation(1 / resistance, "S"))
        lengths = np.linspace(0, 100, 120)
        figure = go.Figure(go.Scatter(x=lengths, y=rho * lengths / (area * 1e-6), mode="lines", line={"color": PANEL, "width": 4}, fill="tozeroy", fillcolor="rgba(139,106,143,.12)", hovertemplate="L = %{x:.1f} m<br>R = %{y:.4f} Ω<extra></extra>"))
        figure.add_trace(go.Scatter(x=[length], y=[resistance], mode="markers", marker={"color": ACCENT, "size": 13, "line": {"color": "white", "width": 3}}, name="Consulta", hovertemplate="L = %{x:.1f} m<br>R = %{y:.4f} Ω<extra></extra>"))
        _plot(_style_figure(figure, title=f"Resistencia de un conductor de {material.lower()}", x_title="Longitud (m)", y_title="Resistencia (Ω)"), "wire_resistance")

    with st.expander("Decodificar un resistor de cuatro bandas", expanded=False):
        color_data = {"Negro": (0, "#202025"), "Marrón": (1, "#76513b"), "Rojo": (2, "#c94645"), "Naranja": (3, "#e48735"), "Amarillo": (4, "#e6bf37"), "Verde": (5, "#4c8b65"), "Azul": (6, "#4779b8"), "Violeta": (7, "#7953a6"), "Gris": (8, "#8d9299"), "Blanco": (9, "#f2f2ee")}
        multipliers = {"Plata ×0,01": (0.01, "#b9bec6"), "Oro ×0,1": (0.1, "#c6a24a"), **{f"{name} ×10^{digit}": (10**digit, color) for name, (digit, color) in color_data.items()}}
        tolerances = {"Marrón ±1 %": (1, "#76513b"), "Rojo ±2 %": (2, "#c94645"), "Oro ±5 %": (5, "#c6a24a"), "Plata ±10 %": (10, "#b9bec6")}
        columns = st.columns(4)
        with columns[0]:
            band1 = st.selectbox("1.ª cifra", [name for name, (digit, _) in color_data.items() if digit != 0], key="band_1")
        with columns[1]:
            band2 = st.selectbox("2.ª cifra", list(color_data), key="band_2")
        with columns[2]:
            multiplier_name = st.selectbox("Multiplicador", list(multipliers), index=5, key="band_m")
        with columns[3]:
            tolerance_name = st.selectbox("Tolerancia", list(tolerances), index=2, key="band_t")
        value = (10 * color_data[band1][0] + color_data[band2][0]) * multipliers[multiplier_name][0]
        tolerance = tolerances[tolerance_name][0]
        band_colors = [color_data[band1][1], color_data[band2][1], multipliers[multiplier_name][1], tolerances[tolerance_name][1]]
        render_html(f'<div class="resistor-decoder"><div class="resistor-lead"></div><div class="resistor-body">{"".join(f"<i style=\"background:{color}\"></i>" for color in band_colors)}</div><div class="resistor-lead"></div><div class="resistor-result"><strong>{engineering_notation(value, "Ω")}</strong><span>± {tolerance:g} %</span></div></div>')
    _source_box("pp. 51–52, 64–67", "3.1 Introdução; 3.2 Resistência; 3.6 Código de cores; 3.7 Condutância")


def _article_ohm() -> None:
    _article_index([("relacao", "Relación"), ("interpretacao", "Interpretación"), ("grafico", "Gráfico V–I"), ("ferramenta", "Herramienta")])
    _fact_sheet([("Relación", "V = RI"), ("Variables", "V, I, R"), ("Validez básica", "Elemento óhmico, R constante"), ("Gráfico V(I)", "Pendiente = R")])

    _section("relacao", "Relación", "Ley de Ohm")
    st.markdown("La Ley de Ohm relaciona corriente, diferencia de potencial y resistencia. Para una resistencia fija, la corriente aumenta con la tensión; para una tensión fija, disminuye al aumentar la resistencia. **(BOYLESTAD, 2012, pp. 84–85).**")
    equations = st.columns(3)
    equations[0].latex(r"V=RI")
    equations[1].latex(r"I=\frac{V}{R}")
    equations[2].latex(r"R=\frac{V}{I}")

    _section("interpretacao", "Lectura", "Dependencias directas")
    _reference_table(["Condición", "Consecuencia"], [["R constante", "I ∝ V"], ["V constante", "I ∝ 1/R"], ["I constante", "V ∝ R"], ["V = 0", "I = 0 para R finita"]])
    _note("Convención de polaridad", "En un resistor pasivo, la corriente de referencia entra por el terminal señalado como positivo para la caída de tensión. Esta convención aparece en Boylestad (2012, p. 86).")

    _section("grafico", "Representación", "Característica V–I")
    st.markdown("En una gráfica de **V en función de I**, una recta indica resistencia constante y su pendiente corresponde a R. Si los ejes se invierten y se representa I(V), la pendiente corresponde a G = 1/R. **(BOYLESTAD, 2012, pp. 86–87).**")

    _section("ferramenta", "Herramienta", "Consulta gráfica V–I")
    with st.expander("Abrir gráfico de la Ley de Ohm", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            resistance = st.slider("Resistencia R (Ω)", 10, 1000, 220, 10, key="ohm_r")
        with c2:
            voltage = st.slider("Tensión aplicada V (V)", 0.0, 120.0, 24.0, 1.0, key="ohm_v")
        current = voltage / resistance
        metrics = st.columns(3)
        metrics[0].metric("V", engineering_notation(voltage, "V"))
        metrics[1].metric("I", engineering_notation(current, "A"))
        metrics[2].metric("R", engineering_notation(resistance, "Ω"))
        current_axis = np.linspace(0, 120 / min(resistance, max(resistance / 2, 1)), 140)
        figure = go.Figure()
        for compared_r, label, color, width in [(resistance / 2, "R/2", "#c8b7cb", 2), (resistance, "R elegida", PANEL, 4), (resistance * 2, "2R", "#d8cedb", 2)]:
            figure.add_trace(go.Scatter(x=current_axis, y=compared_r * current_axis, mode="lines", name=f"{label} = {compared_r:g} Ω", line={"color": color, "width": width}, hovertemplate=f"{label}<br>I = %{{x:.4f}} A<br>V = %{{y:.2f}} V<extra></extra>"))
        figure.add_trace(go.Scatter(x=[current], y=[voltage], mode="markers", name="Punto consultado", marker={"color": ACCENT, "size": 15, "line": {"color": "white", "width": 3}}, hovertemplate="I = %{x:.4f} A<br>V = %{y:.2f} V<extra></extra>"))
        figure.update_yaxes(range=[0, 126])
        _plot(_style_figure(figure, title="Característica tensión–corriente", x_title="Corriente I (A)", y_title="Tensión V (V)"), "ohm")
    _source_box("pp. 84–87", "4.2 Lei de Ohm; 4.3 Gráfico da lei de Ohm")


def _article_power_energy() -> None:
    _article_index([("definiciones", "Definiciones"), ("ecuaciones", "Ecuaciones"), ("eficiencia", "Eficiencia"), ("herramienta", "Herramienta")])
    _fact_sheet([("Potencia", "P · watt (W)"), ("Energía", "W · joule (J), Wh o kWh"), ("Eficiencia", "η · adimensional o %"), ("Equivalencia", "1 W = 1 J/s")])

    _section("definiciones", "Definiciones", "Potencia y energía")
    st.markdown("La **potencia** expresa la rapidez con la que se realiza trabajo o se convierte energía; su unidad es el watt, equivalente a un joule por segundo. **(BOYLESTAD, 2012, p. 89).**\n\nLa **energía** corresponde a la potencia acumulada durante un intervalo. Para potencia constante, se obtiene mediante el producto P·t. **(BOYLESTAD, 2012, p. 91).**")

    _section("ecuaciones", "Formulario", "Relaciones fundamentales")
    _reference_table(
        ["Relación", "Uso"],
        [["P = W/t", "Definición general de potencia"], ["P = VI", "Tensión y corriente conocidas"], ["P = V²/R", "Carga resistiva con V y R"], ["P = I²R", "Carga resistiva con I y R"], ["W = Pt", "Energía para potencia constante"], ["E(Wh) = P(W)·t(h)", "Consumo en watt-hora"]],
    )

    _section("eficiencia", "Rendimiento", "Eficiencia de conversión")
    st.latex(r"\eta=\frac{P_{salida}}{P_{entrada}}\qquad 0\leq\eta\leq1")
    st.markdown("La diferencia entre la potencia de entrada y la potencia útil de salida corresponde a pérdidas o almacenamiento interno. **(BOYLESTAD, 2012, pp. 93–94).**")

    _section("herramienta", "Herramienta", "Calculadora de carga resistiva")
    with st.expander("Abrir calculadora de potencia y energía", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            voltage = st.slider("Tensión (V)", 0.0, 240.0, 127.0, 1.0, key="power_v")
        with c2:
            resistance = st.slider("Resistencia (Ω)", 10.0, 1000.0, 160.0, 10.0, key="power_r")
        with c3:
            hours = st.slider("Tiempo (h)", 0.5, 24.0, 4.0, 0.5, key="power_h")
        current = voltage / resistance
        power = voltage**2 / resistance
        metrics = st.columns(3)
        metrics[0].metric("Corriente", engineering_notation(current, "A"))
        metrics[1].metric("Potencia", engineering_notation(power, "W"))
        metrics[2].metric("Energía", engineering_notation(power * hours, "Wh"))
        voltage_axis = np.linspace(0, 240, 140)
        figure = go.Figure(go.Scatter(x=voltage_axis, y=voltage_axis**2 / resistance, mode="lines", line={"color": PANEL, "width": 4}, fill="tozeroy", fillcolor="rgba(139,106,143,.13)", hovertemplate="V = %{x:.1f} V<br>P = %{y:.1f} W<extra></extra>"))
        figure.add_trace(go.Scatter(x=[voltage], y=[power], mode="markers", name="Consulta", marker={"size": 14, "color": ACCENT, "line": {"color": "white", "width": 3}}, hovertemplate="V = %{x:.1f} V<br>P = %{y:.1f} W<extra></extra>"))
        _plot(_style_figure(figure, title=f"Potencia para R = {resistance:g} Ω", x_title="Tensión (V)", y_title="Potencia (W)"), "power_curve")
    _source_box("pp. 89–94", "4.4 Potência; 4.5 Energia; 4.6 Eficiência")


def _article_consumption() -> None:
    _article_index([("distincao", "kW y kWh"), ("calculo", "Cálculo"), ("medicao", "Medición"), ("ferramenta", "Herramienta")])
    _fact_sheet([("Potencia", "kW · rapidez de consumo"), ("Energía", "kWh · consumo acumulado"), ("Medición", "Medidor de energía"), ("Costo básico", "E × tarifa")])

    _section("distincao", "Concepto", "Potencia nominal y energía consumida")
    st.markdown("La potencia nominal indica la rapidez con la que un equipo utiliza o convierte energía mientras opera. El **kilowatt-hora** mide la energía acumulada durante el uso. Boylestad define 1 kWh como la energía asociada a 1.000 W durante una hora; por ejemplo, equivale a una carga de 100 W durante 10 h. **(BOYLESTAD, 2012, p. 91).**")
    _note("Error de unidad frecuente", "Una vivienda consume kWh durante un período; kW expresa la potencia instantánea o nominal de sus cargas.", "warning")

    _section("calculo", "Cálculo", "Energía y costo básico")
    st.latex(r"E\,(kWh)=\frac{P\,(W)\,t\,(h)}{1000}")
    _reference_table(["Dato", "Cálculo"], [["Varios equipos iguales", "Ptotal = cantidad × Punitaria"], ["Uso diario", "Ediaria = Ptotal × horas/día"], ["Período", "Eperíodo = Ediaria × días"], ["Costo de energía", "Costo = Eperíodo × tarifa de energía"]])

    _section("medicao", "Medición", "Lectura del consumo")
    st.markdown("El medidor de kWh registra la energía eléctrica suministrada a una instalación. La diferencia entre dos lecturas representa el consumo del período. **(BOYLESTAD, 2012, pp. 91–92).**")
    _note("Alcance del costo calculado", "La multiplicación kWh × tarifa representa únicamente la parcela energética informada. Una factura real puede incluir red, tributos, bandeiras tarifarias y otros cargos.")

    _section("ferramenta", "Herramienta", "Estimador de consumo")
    with st.expander("Abrir estimador de kWh y costo", expanded=False):
        presets = {"Lámpara LED": 12, "Ventilador": 80, "Notebook": 65, "Televisor": 120, "Ducha eléctrica": 5500, "Personalizado": 500}
        c1, c2, c3 = st.columns(3)
        with c1:
            appliance = st.selectbox("Equipo", list(presets), key="appliance")
            power = st.number_input("Potencia por equipo (W)", min_value=1.0, value=float(presets[appliance]), step=10.0, key=f"consumption_power_{appliance}")
        with c2:
            quantity = st.number_input("Cantidad", min_value=1, max_value=100, value=1, step=1, key="appliance_quantity")
            hours_day = st.slider("Uso diario (h/día)", 0.1, 24.0, 4.0, 0.1, key="hours_day")
        with c3:
            days = st.slider("Días", 1, 31, 30, 1, key="days_use")
            tariff = st.number_input("Tarifa de energía (R$/kWh)", min_value=0.0, value=0.95, step=0.05, format="%.2f", key="tariff")
        daily_energy = power * quantity * hours_day / 1000
        total_energy = daily_energy * days
        cost = total_energy * tariff
        metrics = st.columns(3)
        metrics[0].metric("Energía diaria", f"{daily_energy:.2f} kWh")
        metrics[1].metric("Energía del período", f"{total_energy:.2f} kWh")
        metrics[2].metric("Costo energético", f"R$ {cost:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        days_axis = np.arange(0, days + 1)
        figure = go.Figure(go.Scatter(x=days_axis, y=daily_energy * days_axis, mode="lines+markers", line={"color": PANEL, "width": 4}, marker={"size": 5, "color": ACCENT}, fill="tozeroy", fillcolor="rgba(139,106,143,.13)", hovertemplate="Día %{x}<br>E = %{y:.2f} kWh<extra></extra>"))
        _plot(_style_figure(figure, title=f"Consumo acumulado · {appliance}", x_title="Día", y_title="Energía acumulada (kWh)"), "consumption")
    _source_box("pp. 91–94", "4.5 Energia; ejemplos 4.10–4.14; tabla 4.1")


def _article_open_short() -> None:
    _article_index([("estados", "Estados"), ("medidores", "Medidores"), ("modelos", "Modelos ideales"), ("herramienta", "Herramienta")])
    _fact_sheet([("Abierto ideal", "R → ∞; I = 0"), ("Corto ideal", "R → 0; V = 0"), ("Voltímetro", "Conexión en paralelo"), ("Amperímetro", "Conexión en serie")])

    _section("estados", "Comparación", "Circuito abierto y cortocircuito")
    _reference_table(
        ["Condición", "Resistencia ideal", "Corriente", "Tensión entre terminales"],
        [["Circuito abierto", "∞", "0 A", "Determinada por la red"], ["Operación normal", "R de carga", "Determinada por V/R", "Determinada por la red"], ["Cortocircuito", "0 Ω", "Determinada por la red externa", "0 V"]],
    )
    st.markdown("Boylestad destaca que una rama abierta siempre tiene corriente nula, aunque puede mantener tensión entre sus terminales. En un corto ideal, la tensión es nula y la corriente queda limitada por el resto de la red. **(BOYLESTAD, 2012, pp. 179–180).**")

    _section("medidores", "Instrumentación", "Conexión correcta")
    _reference_table(
        ["Instrumento", "Magnitud", "Conexión", "Resistencia interna ideal"],
        [["Voltímetro", "Diferencia de potencial", "Paralelo entre dos puntos", "Infinita"], ["Amperímetro", "Corriente de una rama", "Serie con la rama", "Nula"]],
    )
    st.markdown("El voltímetro se conecta entre los dos puntos cuya diferencia de potencial se desea medir; el amperímetro se inserta en la trayectoria para que la corriente lo atraviese. **(BOYLESTAD, 2012, pp. 42–43).**")
    _note("Conexión crítica", "Conectar un amperímetro directamente en paralelo con una fuente aproxima una condición de cortocircuito y puede dañar el instrumento o la instalación.", "warning")

    _section("modelos", "Modelo", "Idealización y sistema real")
    st.markdown("La corriente infinita del cortocircuito solo aparece si se combinan una fuente ideal y resistencia exactamente nula. En una red real, resistencias internas, cables, contactos y protecciones limitan la corriente, aunque esta puede seguir siendo peligrosamente elevada.")

    _section("herramienta", "Herramienta", "Comparador de estados")
    with st.expander("Abrir comparador abierto–normal–corto", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            source_voltage = st.slider("Tensión de la fuente (V)", 1.0, 48.0, 12.0, 1.0, key="state_v")
        with c2:
            load_r = st.slider("Resistencia de carga (Ω)", 1.0, 100.0, 12.0, 1.0, key="state_load")
        with c3:
            internal_r = st.slider("Resistencia interna (Ω)", 0.05, 2.0, 0.20, 0.05, key="state_internal")
        normal_i = source_voltage / (internal_r + load_r)
        short_i = source_voltage / internal_r
        figure = go.Figure(go.Bar(x=["Abierto", "Normal", "Corto"], y=[0, normal_i, short_i], marker_color=["#d8cedb", PANEL, "#c75b59"], text=["0 A", engineering_notation(normal_i, "A"), engineering_notation(short_i, "A")], textposition="outside", hovertemplate="%{x}<br>I = %{y:.3f} A<extra></extra>"))
        figure.update_yaxes(range=[0, short_i * 1.18])
        _plot(_style_figure(figure, title="Corriente según el estado del circuito", x_title="Estado", y_title="Corriente (A)"), "circuit_states")
    _source_box("pp. 42–43 y 179–180", "2.10 Amperímetros e voltímetros; 6.8 Circuitos abertos e curtos-circuitos")


ARTICLE_RENDERERS = {
    "que-es-un-circuito": _article_circuit,
    "tension-y-corriente": _article_voltage_current,
    "resistencia": _article_resistance,
    "ley-de-ohm": _article_ohm,
    "potencia-y-energia": _article_power_energy,
    "consumo-electrico": _article_consumption,
    "abierto-corto-medicion": _article_open_short,
}


def main() -> None:
    _render_topbar()
    unit = get_unit(_query_value("unit"))
    topic = get_topic(unit, _query_value("topic"))
    if topic is None or not topic.available:
        _render_hub(unit)
        return

    _render_article_header(unit, topic)
    renderer = ARTICLE_RENDERERS.get(topic.key)
    if renderer is None:
        st.info("Entrada indexada; contenido pendiente de publicación.")
    else:
        renderer()
    _render_article_footer(unit, topic)


main()
