"""Libro digital interactivo del módulo ``Aprenda la Teoría``.

Versión 0.2: biblioteca completa de unidades y primera unidad funcional.
"""

from __future__ import annotations

from html import escape
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
    topic_position,
)


configure_page(subtitle="Aprenda la Teoría")
load_global_style()


PANEL = "#8b6a8f"
PANEL_DEEP = "#6f5273"
ACCENT = "#532458"
INK = "#211c26"
MUTED = "#6b6472"
LINE = "#ece8ef"
SOFT = "#f6f3f7"
GREEN = "#2f7d63"
AMBER = "#b36b20"

PLOT_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
    "scrollZoom": False,
}


def _query_value(name: str) -> str | None:
    """Lee un parámetro tanto en versiones nuevas como antiguas de Streamlit."""

    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _style_figure(
    figure: go.Figure,
    *,
    title: str,
    x_title: str,
    y_title: str,
    height: int = 390,
) -> go.Figure:
    """Aplica la identidad visual de la plataforma a un gráfico Plotly."""

    figure.update_layout(
        title={"text": title, "x": 0.02, "xanchor": "left"},
        height=height,
        margin={"l": 58, "r": 28, "t": 72, "b": 56},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"family": "Inter, sans-serif", "color": INK, "size": 13},
        title_font={"family": "Poppins, sans-serif", "color": ACCENT, "size": 18},
        hoverlabel={"bgcolor": "#ffffff", "font_color": INK},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    )
    figure.update_xaxes(
        title=x_title,
        showgrid=True,
        gridcolor="#eee9f0",
        zerolinecolor="#d8cedb",
        linecolor="#d8cedb",
    )
    figure.update_yaxes(
        title=y_title,
        showgrid=True,
        gridcolor="#eee9f0",
        zerolinecolor="#d8cedb",
        linecolor="#d8cedb",
    )
    return figure


def _plot(figure: go.Figure, key: str) -> None:
    st.plotly_chart(
        figure,
        width="stretch",
        config=PLOT_CONFIG,
        key=f"theory_plot_{key}",
    )


def _section(number: str, title: str, text: str = "") -> None:
    render_html(
        f"""
        <div class="lesson-section-title">
          <span>{escape(number)}</span>
          <div>
            <h2>{escape(title)}</h2>
            {f'<p>{escape(text)}</p>' if text else ''}
          </div>
        </div>
        """
    )


def _callout(kind: str, title: str, body: str) -> None:
    icons = {"idea": "✦", "warning": "!", "memory": "✓", "example": "→"}
    render_html(
        f"""
        <aside class="lesson-callout lesson-callout--{escape(kind)}">
          <div class="lesson-callout__icon">{icons.get(kind, '•')}</div>
          <div><strong>{escape(title)}</strong><p>{body}</p></div>
        </aside>
        """
    )


def _objectives(items: list[str]) -> None:
    cards = "".join(
        f'<li><span>✓</span>{escape(item)}</li>' for item in items
    )
    render_html(
        f"""
        <section class="lesson-objectives">
          <div class="lesson-objectives__label">Al terminar podrá</div>
          <ul>{cards}</ul>
        </section>
        """
    )


def _concept_cards(cards: list[tuple[str, str, str]]) -> None:
    html = "".join(
        f"""
        <article class="concept-card">
          <span class="concept-card__icon">{icon}</span>
          <h3>{escape(title)}</h3>
          <p>{body}</p>
        </article>
        """
        for icon, title, body in cards
    )
    render_html(f'<div class="concept-grid">{html}</div>')


def _quick_check(
    key: str,
    question: str,
    options: list[str],
    correct: str,
    explanation: str,
) -> None:
    render_html(
        f"""
        <div class="quick-check-head">
          <span>Compruebe lo aprendido</span>
          <h3>{escape(question)}</h3>
        </div>
        """
    )
    answer = st.radio(
        "Seleccione una respuesta",
        options,
        index=None,
        key=f"check_{key}",
        label_visibility="collapsed",
    )
    if answer is None:
        st.caption("Elija una opción para ver la explicación.")
    elif answer == correct:
        st.success(f"¡Correcto! {explanation}")
    else:
        st.error(f"Todavía no. {explanation}")


def _summary(items: list[str]) -> None:
    pills = "".join(f"<li>{item}</li>" for item in items)
    render_html(
        f"""
        <section class="lesson-summary">
          <span>En pocas palabras</span>
          <ul>{pills}</ul>
        </section>
        """
    )


def _render_topbar() -> None:
    render_html(
        """
        <div class="theory-page-marker" aria-hidden="true"></div>
        <nav class="theory-topbar">
          <a href="../" target="_self">← Inicio</a>
          <div><span>UNILA</span> · Monitoría de Circuitos Eléctricos I</div>
          <span class="theory-version">Versión 0.2</span>
        </nav>
        """
    )


def _render_hub(unit: TheoryUnit) -> None:
    available_count = sum(
        topic.available for current_unit in THEORY_UNITS for topic in current_unit.topics
    )
    total_count = sum(len(current_unit.topics) for current_unit in THEORY_UNITS)
    render_html(
        f"""
        <header class="theory-hero">
          <div class="theory-hero__copy">
            <span class="eyebrow">Módulo 01 · Libro interactivo</span>
            <h1>Aprenda la Teoría</h1>
            <p>Explore los fundamentos de Circuitos Eléctricos I mediante capítulos
            breves, ecuaciones claras, ejemplos y visualizaciones que responden a usted.</p>
            <div class="theory-hero__stats">
              <span><strong>7</strong> unidades</span>
              <span><strong>{available_count}</strong> capítulos disponibles</span>
              <span><strong>{total_count}</strong> capítulos planificados</span>
            </div>
          </div>
          <div class="theory-hero__symbol" aria-hidden="true">
            <span>V</span><b>=</b><span>R</span><b>·</b><span>I</span>
          </div>
        </header>
        """
    )

    _section("01", "Elija una unidad", "Siga la secuencia del semestre o vaya directamente al tema que necesita.")
    unit_keys = [current.key for current in THEORY_UNITS]
    selected_key = st.selectbox(
        "Unidad temática",
        unit_keys,
        index=unit_keys.index(unit.key),
        format_func=lambda key: (
            f"Unidad {get_unit(key).number} · {get_unit(key).title}"
        ),
    )
    if selected_key != unit.key:
        st.query_params["unit"] = selected_key
        if "topic" in st.query_params:
            del st.query_params["topic"]
        st.rerun()

    status = "Disponible ahora" if any(topic.available for topic in unit.topics) else "Próximamente"
    render_html(
        f"""
        <section class="unit-intro">
          <div class="unit-intro__number">{unit.number:02d}</div>
          <div class="unit-intro__copy">
            <div><span class="unit-status">{status}</span><span class="unit-reference">{escape(unit.reference)}</span></div>
            <h2>{escape(unit.title)}</h2>
            <p>{escape(unit.description)}</p>
          </div>
        </section>
        """
    )

    cards = []
    for order, topic in enumerate(unit.topics, start=1):
        if topic.available:
            href = f"?unit={quote(unit.key)}&topic={quote(topic.key)}"
            tag = f'<span class="topic-card__status topic-card__status--ready">{topic.duration}</span>'
            card_tag = "a"
            extra = f' href="{href}" target="_self"'
            cta = "Comenzar <b>→</b>"
            css_class = "topic-card topic-card--ready"
        else:
            tag = '<span class="topic-card__status">Próximamente</span>'
            card_tag = "article"
            extra = ""
            cta = "Contenido planificado"
            css_class = "topic-card topic-card--locked"
        cards.append(
            f"""
            <{card_tag} class="{css_class}"{extra}>
              <div class="topic-card__top"><span class="topic-card__order">{order:02d}</span>{tag}</div>
              <div class="topic-card__icon">{topic.icon}</div>
              <h3>{escape(topic.title)}</h3>
              <p>{escape(topic.description)}</p>
              <div class="topic-card__cta">{cta}</div>
            </{card_tag}>
            """
        )
    render_html(f'<div class="topic-grid">{"".join(cards)}</div>')

    _section("02", "Mapa completo del curso", "Las siete unidades siguen el orden lógico de la disciplina y del libro de referencia.")
    roadmap = "".join(
        f"""
        <a class="roadmap-item {'roadmap-item--active' if item.key == unit.key else ''}"
           href="?unit={quote(item.key)}" target="_self">
          <span>{item.number:02d}</span><b>{escape(item.short_title)}</b><small>{escape(item.reference)}</small>
        </a>
        """
        for item in THEORY_UNITS
    )
    render_html(f'<div class="theory-roadmap">{roadmap}</div>')


def _render_lesson_header(unit: TheoryUnit, topic: TheoryTopic) -> None:
    position = topic_position(unit, topic)
    progress = round(position / len(unit.topics) * 100)
    render_html(
        f"""
        <div class="lesson-toolbar">
          <a href="?unit={quote(unit.key)}" target="_self">← Biblioteca de temas</a>
          <span>Unidad {unit.number} · Capítulo {position} de {len(unit.topics)}</span>
        </div>
        <header class="lesson-hero">
          <div class="lesson-hero__icon">{topic.icon}</div>
          <div class="lesson-hero__copy">
            <span class="eyebrow">{escape(unit.short_title)}</span>
            <h1>{escape(topic.title)}</h1>
            <p>{escape(topic.description)}</p>
            <div class="lesson-meta"><span>Lectura · {topic.duration}</span><span>Nivel inicial</span><span>{escape(unit.reference)}</span></div>
          </div>
          <div class="lesson-progress"><strong>{progress}%</strong><span>de la unidad</span></div>
          <div class="lesson-progressbar"><i style="width:{progress}%"></i></div>
        </header>
        """
    )


def _render_lesson_footer(unit: TheoryUnit, topic: TheoryTopic) -> None:
    position = unit.topics.index(topic)
    previous_topic = unit.topics[position - 1] if position > 0 else None
    next_topic = unit.topics[position + 1] if position + 1 < len(unit.topics) else None

    def nav_card(item: TheoryTopic | None, direction: str) -> str:
        if item is None:
            return '<div class="lesson-nav-card lesson-nav-card--empty"></div>'
        label = "Tema anterior" if direction == "previous" else "Tema siguiente"
        arrow = "←" if direction == "previous" else "→"
        return f"""
        <a class="lesson-nav-card lesson-nav-card--{direction}"
           href="?unit={quote(unit.key)}&topic={quote(item.key)}" target="_self">
          <span>{arrow} {label}</span><strong>{escape(item.title)}</strong>
        </a>
        """

    render_html(
        f'<nav class="lesson-bottom-nav">{nav_card(previous_topic, "previous")}{nav_card(next_topic, "next")}</nav>'
    )


def _simple_circuit_svg(voltage: float, resistance: float, closed: bool, current: float) -> str:
    switch = (
        '<line x1="335" y1="68" x2="395" y2="68" class="wire energized"/>'
        if closed
        else '<line x1="335" y1="68" x2="391" y2="36" class="switch-arm"/>'
    )
    current_label = engineering_notation(current, "A") if closed else "0 A"
    state = "CAMINO CERRADO" if closed else "CAMINO INTERRUMPIDO"
    state_class = "on" if closed else "off"
    return f"""
    <div class="circuit-visual circuit-visual--{state_class}">
      <div class="circuit-state">{state}</div>
      <svg viewBox="0 0 640 270" role="img" aria-label="Circuito simple con fuente, interruptor y resistor">
        <path d="M120 68 H305" class="wire {'energized' if closed else ''}"/>
        <circle cx="320" cy="68" r="7" class="terminal"/>
        <circle cx="410" cy="68" r="7" class="terminal"/>
        {switch}
        <path d="M425 68 H520 V105" class="wire {'energized' if closed else ''}"/>
        <path d="M520 165 V215 H120 V168" class="wire {'energized' if closed else ''}"/>
        <rect x="492" y="105" width="56" height="60" rx="8" class="resistor"/>
        <text x="520" y="135" class="svg-main" text-anchor="middle">R</text>
        <text x="520" y="185" class="svg-small" text-anchor="middle">{resistance:.0f} Ω</text>
        <line x1="120" y1="105" x2="120" y2="132" class="battery-long"/>
        <line x1="96" y1="142" x2="144" y2="142" class="battery-long"/>
        <line x1="104" y1="158" x2="136" y2="158" class="battery-short"/>
        <text x="70" y="147" class="svg-main" text-anchor="middle">{voltage:.0f} V</text>
        <text x="365" y="28" class="svg-small" text-anchor="middle">Interruptor</text>
        <path d="M235 49 h55" class="current-arrow {'visible' if closed else ''}"/>
        <polygon points="290,49 278,42 278,56" class="arrow-head {'visible' if closed else ''}"/>
        <text x="262" y="35" class="svg-small" text-anchor="middle">I = {current_label}</text>
      </svg>
    </div>
    """


def _lesson_circuit() -> None:
    _objectives([
        "Identificar los elementos mínimos de un circuito.",
        "Explicar por qué la corriente necesita un camino cerrado.",
        "Distinguir fuente, conexión, carga y elemento de control.",
    ])
    _section("1.1", "Un camino para transferir energía")
    st.markdown(
        """
Un **circuito eléctrico** es una interconexión de elementos preparada para que
la carga eléctrica pueda desplazarse y la energía sea transferida. En el caso
más sencillo necesitamos una fuente, un camino conductor y una carga.

La fuente establece una diferencia de potencial. Cuando el camino está
cerrado, esa condición puede producir corriente y la carga convierte la energía
eléctrica en luz, calor, movimiento u otra forma útil.
"""
    )
    _concept_cards([
        ("＋", "Fuente", "Entrega energía al circuito y mantiene una diferencia de potencial, como una batería."),
        ("━", "Conductores", "Conectan los elementos y proporcionan un camino de baja resistencia para la carga."),
        ("✦", "Carga", "Recibe energía eléctrica y la transforma: lámpara, resistor, motor o dispositivo electrónico."),
    ])
    _callout(
        "idea",
        "Una fuente aislada no produce corriente por sí sola",
        "Puede existir tensión entre sus terminales incluso con el circuito abierto. La corriente aparece cuando existe un camino cerrado y una diferencia de potencial que la impulse.",
    )

    _section("1.2", "Abra y cierre el circuito", "Modifique la fuente y la carga; después observe qué cambia al accionar el interruptor.")
    left, right = st.columns([1, 1])
    with left:
        voltage = st.slider("Tensión de la fuente (V)", 1.0, 24.0, 12.0, 1.0, key="circuit_voltage")
        resistance = st.slider("Resistencia de la carga (Ω)", 10.0, 500.0, 120.0, 10.0, key="circuit_resistance")
    with right:
        closed = st.toggle("Interruptor cerrado", value=True, key="circuit_closed")
        current = voltage / resistance if closed else 0.0
        st.metric("Corriente del circuito", engineering_notation(current, "A"))
    render_html(_simple_circuit_svg(voltage, resistance, closed, current))

    _section("1.3", "Modelo ideal y circuito real")
    st.markdown(
        """
En los primeros análisis representamos cada elemento mediante un **modelo
ideal**. Los cables tienen resistencia nula, la fuente mantiene exactamente su
tensión y la carga posee un valor definido. Este modelo permite descubrir las
relaciones principales antes de incluir pérdidas y limitaciones reales.
"""
    )
    _callout("warning", "No confunda circuito abierto con circuito apagado", "Un circuito abierto tiene el camino interrumpido y, por eso, corriente nula. Aun así puede existir una tensión peligrosa entre los puntos abiertos.")
    _quick_check(
        "circuit",
        "Una batería está conectada a un resistor por un solo cable. ¿Qué ocurre?",
        ["Circula la corriente nominal", "No circula corriente porque falta el camino de retorno", "El resistor entra en cortocircuito"],
        "No circula corriente porque falta el camino de retorno",
        "La corriente sostenida necesita una trayectoria cerrada que salga de un terminal y regrese al otro.",
    )
    _summary(["La tensión puede existir sin corriente.", "La corriente sostenida requiere un camino cerrado.", "Fuente, conductores y carga forman el circuito básico."])


def _lesson_voltage_current() -> None:
    _objectives([
        "Interpretar tensión como energía por unidad de carga.",
        "Interpretar corriente como rapidez de flujo de carga.",
        "Usar correctamente voltios, amperios y sentidos de referencia.",
    ])
    _section("2.1", "Dos magnitudes diferentes")
    columns = st.columns(2)
    with columns[0]:
        st.markdown("#### Tensión eléctrica")
        st.markdown("Mide la diferencia de energía potencial eléctrica por unidad de carga entre dos puntos.")
        st.latex(r"V=\frac{W}{Q}\qquad [V]=\frac{J}{C}")
    with columns[1]:
        st.markdown("#### Corriente eléctrica")
        st.markdown("Mide cuánta carga atraviesa una sección del conductor por unidad de tiempo.")
        st.latex(r"I=\frac{dQ}{dt}\qquad 1\,A=1\,\frac{C}{s}")
    _callout("idea", "Tensión se mide entre dos puntos; corriente, a través de un elemento", "Esta diferencia determina incluso cómo se conectan los instrumentos de medida: voltímetro en paralelo y amperímetro en serie.")

    _section("2.2", "Observe el flujo de carga", "Elija una cantidad de carga y el tiempo que demora en atravesar una sección.")
    left, right = st.columns(2)
    with left:
        charge = st.slider("Carga transferida Q (C)", 0.5, 20.0, 6.0, 0.5, key="charge_q")
    with right:
        interval = st.slider("Intervalo Δt (s)", 0.5, 10.0, 3.0, 0.5, key="charge_t")
    current = charge / interval
    st.metric("Corriente media", engineering_notation(current, "A"), help="I = ΔQ / Δt")
    time = np.linspace(0, interval, 80)
    transferred = current * time
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=time, y=transferred, mode="lines", fill="tozeroy", line={"color": PANEL, "width": 4}, fillcolor="rgba(139,106,143,.16)", name="Carga transferida", hovertemplate="t = %{x:.2f} s<br>Q = %{y:.2f} C<extra></extra>"))
    figure.add_trace(go.Scatter(x=[interval], y=[charge], mode="markers", marker={"size": 13, "color": ACCENT, "line": {"width": 3, "color": "white"}}, name="Punto elegido", hovertemplate="Δt = %{x:.2f} s<br>ΔQ = %{y:.2f} C<extra></extra>"))
    _plot(_style_figure(figure, title="Carga que atraviesa la sección", x_title="Tiempo (s)", y_title="Carga acumulada (C)"), "charge_flow")

    _section("2.3", "El sentido es una referencia")
    st.markdown(
        """
Por convenio, la **corriente convencional** se dibuja desde el potencial más
alto hacia el más bajo en el circuito externo. Los electrones metálicos se
desplazan en sentido opuesto, pero las ecuaciones de circuitos utilizan la
corriente convencional.

Podemos escoger inicialmente cualquier flecha como referencia. Si el cálculo
entrega un valor negativo, el resultado simplemente indica que la corriente
real circula en el sentido contrario a la flecha elegida.
"""
    )
    _quick_check(
        "voltage_current",
        "Si 12 C atraviesan un conductor durante 4 s, ¿cuál es la corriente media?",
        ["0,33 A", "3 A", "48 A"],
        "3 A",
        "Aplicando I = ΔQ/Δt se obtiene 12 C / 4 s = 3 A.",
    )
    _summary(["V = W/Q: energía por carga.", "I = dQ/dt: rapidez de flujo de carga.", "Una referencia negativa no es un error: revela el sentido real."])


def _lesson_resistance() -> None:
    _objectives([
        "Relacionar resistencia con material y geometría.",
        "Distinguir resistencia de conductancia.",
        "Interpretar el código de cuatro bandas de un resistor.",
    ])
    _section("3.1", "La oposición al movimiento de carga")
    st.markdown(
        """
La **resistencia** describe cuánto se opone un elemento al establecimiento de
corriente. En un conductor uniforme depende de la resistividad del material,
de su longitud y del área transversal.
"""
    )
    st.latex(r"R=\rho\frac{L}{A}\qquad\qquad G=\frac{1}{R}")
    _concept_cards([
        ("ρ", "Material", "Una resistividad mayor produce una resistencia mayor para la misma geometría."),
        ("L", "Longitud", "Un camino más largo dificulta el movimiento: R crece proporcionalmente con L."),
        ("A", "Área", "Una sección mayor ofrece más camino disponible: R disminuye cuando A aumenta."),
    ])

    _section("3.2", "Cambie el conductor", "Compare cómo el material, la longitud y el área modifican la resistencia.")
    materials = {
        "Cobre": 1.68e-8,
        "Aluminio": 2.82e-8,
        "Nicromo": 1.10e-6,
    }
    c1, c2, c3 = st.columns(3)
    with c1:
        material = st.selectbox("Material", list(materials), key="wire_material")
    with c2:
        length = st.slider("Longitud (m)", 1.0, 100.0, 25.0, 1.0, key="wire_length")
    with c3:
        area = st.slider("Área (mm²)", 0.5, 10.0, 2.5, 0.5, key="wire_area")
    rho = materials[material]
    resistance = rho * length / (area * 1e-6)
    conductance = 1 / resistance
    m1, m2 = st.columns(2)
    m1.metric("Resistencia", engineering_notation(resistance, "Ω"))
    m2.metric("Conductancia", engineering_notation(conductance, "S"))
    lengths = np.linspace(0, 100, 120)
    values = rho * lengths / (area * 1e-6)
    figure = go.Figure(go.Scatter(x=lengths, y=values, mode="lines", line={"color": PANEL, "width": 4}, fill="tozeroy", fillcolor="rgba(139,106,143,.12)", hovertemplate="L = %{x:.1f} m<br>R = %{y:.4f} Ω<extra></extra>"))
    figure.add_trace(go.Scatter(x=[length], y=[resistance], mode="markers", marker={"color": ACCENT, "size": 13, "line": {"color": "white", "width": 3}}, name="Conductor elegido", hovertemplate="L = %{x:.1f} m<br>R = %{y:.4f} Ω<extra></extra>"))
    _plot(_style_figure(figure, title=f"Resistencia de un conductor de {material.lower()}", x_title="Longitud (m)", y_title="Resistencia (Ω)"), "wire_resistance")

    _section("3.3", "Lea un resistor de cuatro bandas")
    color_data = {
        "Negro": (0, "#202025"), "Marrón": (1, "#76513b"), "Rojo": (2, "#c94645"),
        "Naranja": (3, "#e48735"), "Amarillo": (4, "#e6bf37"), "Verde": (5, "#4c8b65"),
        "Azul": (6, "#4779b8"), "Violeta": (7, "#7953a6"), "Gris": (8, "#8d9299"), "Blanco": (9, "#f2f2ee"),
    }
    multipliers = {
        "Plata ×0,01": (0.01, "#b9bec6"), "Oro ×0,1": (0.1, "#c6a24a"),
        **{f"{name} ×10^{digit}": (10**digit, color) for name, (digit, color) in color_data.items()},
    }
    tolerances = {"Marrón ±1 %": (1, "#76513b"), "Rojo ±2 %": (2, "#c94645"), "Oro ±5 %": (5, "#c6a24a"), "Plata ±10 %": (10, "#b9bec6")}
    band1_options = [name for name, (digit, _) in color_data.items() if digit != 0]
    bands = st.columns(4)
    with bands[0]:
        band1 = st.selectbox("1.ª cifra", band1_options, index=0, key="band_1")
    with bands[1]:
        band2 = st.selectbox("2.ª cifra", list(color_data), index=0, key="band_2")
    with bands[2]:
        multiplier_name = st.selectbox("Multiplicador", list(multipliers), index=5, key="band_m")
    with bands[3]:
        tolerance_name = st.selectbox("Tolerancia", list(tolerances), index=2, key="band_t")
    value = (10 * color_data[band1][0] + color_data[band2][0]) * multipliers[multiplier_name][0]
    tolerance = tolerances[tolerance_name][0]
    band_colors = [color_data[band1][1], color_data[band2][1], multipliers[multiplier_name][1], tolerances[tolerance_name][1]]
    render_html(
        f"""
        <div class="resistor-decoder">
          <div class="resistor-lead"></div>
          <div class="resistor-body">
            {''.join(f'<i style="background:{color}"></i>' for color in band_colors)}
          </div>
          <div class="resistor-lead"></div>
          <div class="resistor-result"><strong>{engineering_notation(value, 'Ω')}</strong><span>± {tolerance:g} %</span></div>
        </div>
        """
    )
    _quick_check(
        "resistance",
        "Si se duplica la longitud sin cambiar material ni área, ¿qué ocurre con R?",
        ["Se reduce a la mitad", "No cambia", "Se duplica"],
        "Se duplica",
        "En R = ρL/A, la resistencia es directamente proporcional a la longitud.",
    )
    _summary(["R = ρL/A", "Mayor longitud → mayor resistencia.", "Mayor área → menor resistencia.", "G = 1/R se mide en siemens."])


def _lesson_ohm() -> None:
    _objectives([
        "Aplicar las tres formas de la Ley de Ohm.",
        "Leer el punto de operación en un gráfico V–I.",
        "Relacionar la pendiente de V(I) con la resistencia.",
    ])
    _section("4.1", "La relación fundamental")
    st.markdown("Para un elemento óhmico a temperatura constante, la tensión y la corriente son directamente proporcionales. La resistencia es la constante que relaciona ambas magnitudes.")
    equations = st.columns(3)
    equations[0].latex(r"V=R I")
    equations[1].latex(r"I=\frac{V}{R}")
    equations[2].latex(r"R=\frac{V}{I}")
    _callout("memory", "No memorice un triángulo sin pensar en las unidades", "Voltios divididos por ohmios producen amperios; voltios divididos por amperios producen ohmios. Las unidades permiten comprobar la ecuación elegida.")

    _section("4.2", "Construya la característica V–I", "Cambie la resistencia y el punto de operación. Pase el cursor sobre las rectas para leer valores.")
    c1, c2 = st.columns(2)
    with c1:
        resistance = st.slider("Resistencia R (Ω)", 10, 1000, 220, 10, key="ohm_r")
    with c2:
        voltage = st.slider("Tensión aplicada V (V)", 0.0, 120.0, 24.0, 1.0, key="ohm_v")
    current = voltage / resistance
    power = voltage * current
    m1, m2, m3 = st.columns(3)
    m1.metric("Tensión", engineering_notation(voltage, "V"))
    m2.metric("Corriente", engineering_notation(current, "A"))
    m3.metric("Potencia", engineering_notation(power, "W"))
    max_current = 120 / min(resistance, max(resistance / 2, 1))
    current_axis = np.linspace(0, max_current, 140)
    figure = go.Figure()
    comparisons = [(resistance / 2, "R/2", "#c8b7cb", 2), (resistance, "R elegida", PANEL, 4), (resistance * 2, "2R", "#d8cedb", 2)]
    for compared_r, label, color, width in comparisons:
        figure.add_trace(go.Scatter(x=current_axis, y=compared_r * current_axis, mode="lines", name=f"{label} = {compared_r:g} Ω", line={"color": color, "width": width}, hovertemplate=f"{label}<br>I = %{{x:.4f}} A<br>V = %{{y:.2f}} V<extra></extra>"))
    figure.add_trace(go.Scatter(x=[current], y=[voltage], mode="markers", name="Punto de operación", marker={"color": ACCENT, "size": 15, "line": {"color": "white", "width": 3}}, hovertemplate="I = %{x:.4f} A<br>V = %{y:.2f} V<extra></extra>"))
    figure.update_yaxes(range=[0, 126])
    _plot(_style_figure(figure, title="Característica tensión–corriente", x_title="Corriente I (A)", y_title="Tensión V (V)"), "ohm")
    _callout("idea", "En el gráfico V en función de I, la pendiente es R", "Una resistencia mayor produce una recta más inclinada. Si se graficara I en función de V, la pendiente sería la conductancia G = 1/R.")
    _quick_check(
        "ohm",
        "Se mantienen 12 V y la resistencia aumenta de 100 Ω a 200 Ω. ¿Qué sucede con I?",
        ["Se duplica", "Se reduce a la mitad", "Permanece igual"],
        "Se reduce a la mitad",
        "Con tensión fija, I = V/R. Duplicar R divide la corriente por dos.",
    )
    _summary(["V = RI", "Con R fija: V e I son proporcionales.", "Con V fija: aumentar R reduce I.", "En V(I), la pendiente representa R."])


def _lesson_power_energy() -> None:
    _objectives([
        "Diferenciar potencia de energía.",
        "Calcular potencia con V, I o R.",
        "Interpretar eficiencia y el signo de la potencia.",
    ])
    _section("5.1", "¿Cuán rápido se transforma la energía?")
    st.markdown("La **potencia** indica la rapidez con la que un elemento entrega o absorbe energía. La **energía** acumula esa potencia a lo largo del tiempo.")
    st.latex(r"P=\frac{dW}{dt}=VI\qquad\qquad W=\int P\,dt")
    equations = st.columns(3)
    equations[0].latex(r"P=VI")
    equations[1].latex(r"P=I^2R")
    equations[2].latex(r"P=\frac{V^2}{R}")
    _callout("idea", "Watt no es watt-hora", "El watt (W) mide potencia. El watt-hora (Wh) y el joule (J) miden energía. Una carga de 100 W utilizada durante 3 h consume 300 Wh.")

    _section("5.2", "Potencia de una carga resistiva", "Observe la dependencia cuadrática de la potencia con la tensión cuando R permanece fija.")
    c1, c2, c3 = st.columns(3)
    with c1:
        voltage = st.slider("Tensión (V)", 0.0, 240.0, 127.0, 1.0, key="power_v")
    with c2:
        resistance = st.slider("Resistencia (Ω)", 10.0, 1000.0, 160.0, 10.0, key="power_r")
    with c3:
        hours = st.slider("Tiempo de uso (h)", 0.5, 24.0, 4.0, 0.5, key="power_h")
    current = voltage / resistance
    power = voltage**2 / resistance
    energy_wh = power * hours
    metrics = st.columns(3)
    metrics[0].metric("Corriente", engineering_notation(current, "A"))
    metrics[1].metric("Potencia", engineering_notation(power, "W"))
    metrics[2].metric("Energía", engineering_notation(energy_wh, "Wh"))
    voltage_axis = np.linspace(0, 240, 140)
    powers = voltage_axis**2 / resistance
    figure = go.Figure(go.Scatter(x=voltage_axis, y=powers, mode="lines", line={"color": PANEL, "width": 4}, fill="tozeroy", fillcolor="rgba(139,106,143,.13)", hovertemplate="V = %{x:.1f} V<br>P = %{y:.1f} W<extra></extra>"))
    figure.add_trace(go.Scatter(x=[voltage], y=[power], mode="markers", name="Operación", marker={"size": 14, "color": ACCENT, "line": {"color": "white", "width": 3}}, hovertemplate="V = %{x:.1f} V<br>P = %{y:.1f} W<extra></extra>"))
    _plot(_style_figure(figure, title=f"Potencia para R = {resistance:g} Ω", x_title="Tensión (V)", y_title="Potencia (W)"), "power_curve")

    _section("5.3", "Eficiencia")
    st.markdown("Ninguna conversión real es perfecta. La eficiencia compara la potencia útil de salida con la potencia recibida.")
    st.latex(r"\eta=\frac{P_{salida}}{P_{entrada}}\times100\%")
    efficiency = st.slider("Eficiencia del equipo (%)", 10, 100, 85, 1, key="efficiency")
    input_power = st.number_input("Potencia de entrada (W)", min_value=1.0, value=500.0, step=10.0, key="input_power")
    output_power = input_power * efficiency / 100
    loss = input_power - output_power
    e1, e2 = st.columns(2)
    e1.metric("Potencia útil", engineering_notation(output_power, "W"))
    e2.metric("Pérdidas", engineering_notation(loss, "W"))
    _quick_check(
        "power",
        "Una carga consume 60 W durante 5 h. ¿Qué energía utiliza?",
        ["12 Wh", "65 Wh", "300 Wh"],
        "300 Wh",
        "Para potencia constante, W = P·t = 60 W × 5 h = 300 Wh.",
    )
    _summary(["Potencia es rapidez; energía es acumulación.", "P = VI = I²R = V²/R para un resistor.", "W = Pt si P es constante.", "η = Psalida/Pentrada."])


def _lesson_consumption() -> None:
    _objectives([
        "Diferenciar potencia nominal y consumo de energía.",
        "Calcular kWh a partir del tiempo de utilización.",
        "Estimar el costo energético sin confundirlo con la factura completa.",
    ])
    _section("6.1", "Del watt al kilowatt-hora")
    st.markdown("La potencia escrita en la etiqueta de un equipo indica la rapidez con la que utiliza energía mientras funciona. La empresa distribuidora registra la energía acumulada, normalmente en **kWh**.")
    st.latex(r"E\,(kWh)=\frac{P\,(W)}{1000}\;t\,(h)")
    _callout("warning", "kW y kWh no son intercambiables", "kW es potencia; kWh es energía. Decir que una vivienda consumió “200 kW en el mes” mezcla dos conceptos diferentes.")

    _section("6.2", "Calcule un consumo", "El resultado considera solamente el precio de energía informado, no impuestos, tarifas de red ni otras parcelas de una factura real.")
    presets = {
        "Lámpara LED": 12,
        "Ventilador": 80,
        "Notebook": 65,
        "Televisor": 120,
        "Ducha eléctrica": 5500,
        "Personalizado": 500,
    }
    c1, c2, c3 = st.columns(3)
    with c1:
        appliance = st.selectbox("Equipo", list(presets), key="appliance")
        default_power = presets[appliance]
        power = st.number_input("Potencia por equipo (W)", min_value=1.0, value=float(default_power), step=10.0, key=f"consumption_power_{appliance}")
    with c2:
        quantity = st.number_input("Cantidad de equipos", min_value=1, max_value=100, value=1, step=1, key="appliance_quantity")
        hours_day = st.slider("Uso diario (h/día)", 0.1, 24.0, 4.0, 0.1, key="hours_day")
    with c3:
        days = st.slider("Días de uso", 1, 31, 30, 1, key="days_use")
        tariff = st.number_input("Precio de energía (R$/kWh)", min_value=0.0, value=0.95, step=0.05, format="%.2f", key="tariff")
    daily_energy = power * quantity * hours_day / 1000
    total_energy = daily_energy * days
    cost = total_energy * tariff
    metrics = st.columns(3)
    metrics[0].metric("Energía por día", f"{daily_energy:.2f} kWh")
    metrics[1].metric("Energía del período", f"{total_energy:.2f} kWh")
    metrics[2].metric("Costo de energía", f"R$ {cost:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    days_axis = np.arange(0, days + 1)
    cumulative = daily_energy * days_axis
    figure = go.Figure(go.Scatter(x=days_axis, y=cumulative, mode="lines+markers", line={"color": PANEL, "width": 4}, marker={"size": 5, "color": ACCENT}, fill="tozeroy", fillcolor="rgba(139,106,143,.13)", hovertemplate="Día %{x}<br>E = %{y:.2f} kWh<extra></extra>"))
    _plot(_style_figure(figure, title=f"Consumo acumulado · {appliance}", x_title="Día", y_title="Energía acumulada (kWh)"), "consumption")
    _callout("example", "Lectura física del resultado", f"Los {quantity} equipos suman {engineering_notation(power * quantity, 'W')} de potencia mientras están encendidos. Cada día agregan {daily_energy:.2f} kWh al medidor.")
    _quick_check(
        "consumption",
        "Dos lámparas de 10 W funcionan durante 5 h. ¿Cuál es el consumo total?",
        ["0,01 kWh", "0,10 kWh", "100 kWh"],
        "0,10 kWh",
        "E = (2 × 10 W / 1000) × 5 h = 0,10 kWh.",
    )
    _summary(["La etiqueta del equipo informa potencia.", "El medidor acumula energía.", "E(kWh) = P(W)t(h)/1000.", "Costo de energía = kWh × precio unitario."])


def _lesson_open_short() -> None:
    _objectives([
        "Distinguir operación normal, circuito abierto y cortocircuito.",
        "Comprender por qué un corto real produce corriente elevada.",
        "Conectar amperímetro y voltímetro sin alterar indebidamente el circuito.",
    ])
    _section("7.1", "Tres estados muy diferentes")
    _concept_cards([
        ("○", "Circuito abierto", "Resistencia equivalente idealmente infinita y corriente igual a cero."),
        ("✓", "Operación normal", "La carga limita la corriente y recibe una tensión determinada por el circuito."),
        ("!", "Cortocircuito", "Camino de resistencia muy baja; la corriente queda limitada por resistencias internas y conductores."),
    ])
    _callout("warning", "Un cortocircuito no significa tensión alta", "Entre los extremos de un corto ideal la tensión es cero. El peligro surge por la corriente extremadamente elevada, el calentamiento, el arco y los esfuerzos sobre la fuente y los conductores.")

    _section("7.2", "Compare los estados", "Incluimos una resistencia interna pequeña para representar una fuente real y evitar la corriente infinita del modelo ideal.")
    c1, c2, c3 = st.columns(3)
    with c1:
        source_voltage = st.slider("Tensión de la fuente (V)", 1.0, 48.0, 12.0, 1.0, key="state_v")
    with c2:
        load_r = st.slider("Resistencia de carga (Ω)", 1.0, 100.0, 12.0, 1.0, key="state_load")
    with c3:
        internal_r = st.slider("Resistencia interna (Ω)", 0.05, 2.0, 0.20, 0.05, key="state_internal")
    normal_i = source_voltage / (internal_r + load_r)
    short_i = source_voltage / internal_r
    states = ["Abierto", "Normal", "Corto"]
    currents = [0, normal_i, short_i]
    figure = go.Figure(go.Bar(x=states, y=currents, marker_color=["#d8cedb", PANEL, "#c75b59"], text=["0 A", engineering_notation(normal_i, "A"), engineering_notation(short_i, "A")], textposition="outside", hovertemplate="%{x}<br>I = %{y:.3f} A<extra></extra>"))
    figure.update_yaxes(range=[0, short_i * 1.18])
    _plot(_style_figure(figure, title="Corriente según el estado del circuito", x_title="Estado", y_title="Corriente (A)"), "circuit_states")
    ratio = short_i / normal_i
    _callout("idea", "La corriente de corto domina la escala", f"Con estos valores, el cortocircuito produce aproximadamente {ratio:.1f} veces la corriente normal. En sistemas reales actúan fusibles, disyuntores y otras protecciones.")

    _section("7.3", "Cómo conectar los instrumentos")
    _concept_cards([
        ("A", "Amperímetro en serie", "La corriente que desea medir debe atravesarlo. Idealmente posee resistencia interna nula."),
        ("V", "Voltímetro en paralelo", "Se conecta entre los dos puntos cuya diferencia de potencial se desea medir. Idealmente posee resistencia infinita."),
    ])
    _callout("warning", "Conexión peligrosa", "Nunca conecte un amperímetro directamente en paralelo con una fuente: su resistencia muy baja crea una condición próxima al cortocircuito.")
    _quick_check(
        "open_short",
        "¿Dónde se conecta un voltímetro para medir la caída en un resistor?",
        ["En serie con el resistor", "En paralelo con el resistor", "En paralelo con un amperímetro desconectado"],
        "En paralelo con el resistor",
        "El voltímetro compara el potencial de los dos terminales del resistor y, por eso, se conecta en paralelo.",
    )
    _summary(["Abierto ideal: I = 0.", "Corto ideal: V = 0 entre sus extremos.", "El amperímetro se conecta en serie.", "El voltímetro se conecta en paralelo."])


LESSON_RENDERERS = {
    "que-es-un-circuito": _lesson_circuit,
    "tension-y-corriente": _lesson_voltage_current,
    "resistencia": _lesson_resistance,
    "ley-de-ohm": _lesson_ohm,
    "potencia-y-energia": _lesson_power_energy,
    "consumo-electrico": _lesson_consumption,
    "abierto-corto-medicion": _lesson_open_short,
}


def main() -> None:
    _render_topbar()
    unit = get_unit(_query_value("unit"))
    topic = get_topic(unit, _query_value("topic"))

    if topic is None or not topic.available:
        _render_hub(unit)
        return

    _render_lesson_header(unit, topic)
    renderer = LESSON_RENDERERS.get(topic.key)
    if renderer is None:
        st.info("Este capítulo está preparado en el catálogo y recibirá contenido próximamente.")
    else:
        renderer()
    _render_lesson_footer(unit, topic)


main()
