"""Catálogo y utilidades del módulo ``Aprenda la Teoría``.

El catálogo vive fuera de la página para que, a medida que el curso crezca,
la navegación y el contenido sigan siendo fáciles de mantener.  Los textos de
las lecciones son originales y usan Boylestad (12.ª edición) como referencia
de secuencia y alcance, no como contenido copiado.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TheoryTopic:
    """Metadatos de un capítulo breve dentro de una unidad."""

    key: str
    title: str
    description: str
    icon: str
    duration: str = "8 min"
    available: bool = False


@dataclass(frozen=True)
class TheoryUnit:
    """Unidad temática mostrada en el selector y en la biblioteca."""

    key: str
    number: int
    title: str
    short_title: str
    description: str
    reference: str
    icon: str
    topics: tuple[TheoryTopic, ...]


THEORY_UNITS: tuple[TheoryUnit, ...] = (
    TheoryUnit(
        key="fundamentos-cc",
        number=1,
        title="Fundamentos de circuitos en CC",
        short_title="Fundamentos en CC",
        description=(
            "Construya la base: circuito eléctrico, tensión, corriente, "
            "resistencia, Ley de Ohm, potencia, energía y consumo."
        ),
        reference="Boylestad · capítulos 2–4",
        icon="⚡",
        topics=(
            TheoryTopic(
                "que-es-un-circuito",
                "¿Qué es un circuito eléctrico?",
                "Fuentes, conductores, cargas y la necesidad de un camino cerrado.",
                "🔌",
                "7 min",
                True,
            ),
            TheoryTopic(
                "tension-y-corriente",
                "Tensión y corriente",
                "Diferencia de potencial, movimiento de carga y sentidos de referencia.",
                "↗",
                "9 min",
                True,
            ),
            TheoryTopic(
                "resistencia",
                "Resistencia y resistores",
                "Qué limita la corriente, de qué depende R y cómo leer un resistor.",
                "〰",
                "10 min",
                True,
            ),
            TheoryTopic(
                "ley-de-ohm",
                "Ley de Ohm",
                "Relacione V, I y R y descubra qué representa la pendiente del gráfico.",
                "Ω",
                "10 min",
                True,
            ),
            TheoryTopic(
                "potencia-y-energia",
                "Potencia, energía y eficiencia",
                "Comprenda la rapidez de conversión de energía y sus ecuaciones.",
                "💡",
                "10 min",
                True,
            ),
            TheoryTopic(
                "consumo-electrico",
                "Consumo eléctrico",
                "Diferencie kW de kWh y estime energía y costo de utilización.",
                "🧾",
                "8 min",
                True,
            ),
            TheoryTopic(
                "abierto-corto-medicion",
                "Circuito abierto, corto y medición",
                "Compare estados del circuito y conecte amperímetro y voltímetro.",
                "🧰",
                "10 min",
                True,
            ),
        ),
    ),
    TheoryUnit(
        key="circuitos-resistivos",
        number=2,
        title="Circuitos resistivos",
        short_title="Circuitos resistivos",
        description=(
            "Analice asociaciones en serie, paralelo y serie–paralelo usando "
            "resistencia equivalente y las leyes de Kirchhoff."
        ),
        reference="Boylestad · capítulos 5–7",
        icon="⛓",
        topics=(
            TheoryTopic("serie", "Circuitos en serie", "Corriente común, caídas de tensión y resistencia equivalente.", "━"),
            TheoryTopic("paralelo", "Circuitos en paralelo", "Tensión común, reparto de corriente y conductancia.", "⋕"),
            TheoryTopic("mixtos", "Circuitos serie–paralelo", "Reducción y retorno para redes resistivas mixtas.", "⌁"),
            TheoryTopic("kvl", "Ley de Kirchhoff para tensiones", "Balance de elevaciones y caídas en un camino cerrado.", "Σ"),
            TheoryTopic("kcl", "Ley de Kirchhoff para corrientes", "Conservación de carga en nodos eléctricos.", "↔"),
            TheoryTopic("divisores", "Divisores de tensión y corriente", "Relaciones rápidas para asociaciones básicas.", "÷"),
        ),
    ),
    TheoryUnit(
        key="metodos-cc",
        number=3,
        title="Métodos de análisis en CC",
        short_title="Métodos de análisis",
        description=(
            "Formule y resuelva circuitos que ya no pueden reducirse solamente "
            "con asociaciones serie–paralelo."
        ),
        reference="Boylestad · capítulo 8 + ampliación didáctica",
        icon="🧠",
        topics=(
            TheoryTopic("topologia", "Ramas, nodos y mallas", "Reconozca la topología antes de escribir ecuaciones.", "◫"),
            TheoryTopic("nodal", "Análisis nodal", "Encuentre tensiones desconocidas aplicando KCL.", "●"),
            TheoryTopic("supernodos", "Supernodos", "Trate fuentes de tensión entre dos nodos no conocidos.", "◉"),
            TheoryTopic("mallas", "Análisis de mallas", "Encuentre corrientes desconocidas aplicando KVL.", "↻"),
            TheoryTopic("supermallas", "Supermallas", "Trate fuentes de corriente compartidas entre mallas.", "◎"),
        ),
    ),
    TheoryUnit(
        key="teoremas",
        number=4,
        title="Teoremas de circuitos",
        short_title="Teoremas de circuitos",
        description=(
            "Simplifique redes y estudie su efecto sobre una carga mediante "
            "equivalentes y principios fundamentales."
        ),
        reference="Boylestad · capítulo 9",
        icon="🧩",
        topics=(
            TheoryTopic("superposicion", "Superposición", "Separe el efecto de cada fuente independiente.", "+"),
            TheoryTopic("thevenin", "Teorema de Thévenin", "Represente una red mediante una fuente y una resistencia en serie.", "T"),
            TheoryTopic("norton", "Teorema de Norton", "Represente una red mediante una fuente y una resistencia en paralelo.", "N"),
            TheoryTopic("maxima-potencia", "Máxima transferencia de potencia", "Determine la carga que recibe la máxima potencia.", "P"),
        ),
    ),
    TheoryUnit(
        key="capacitores-inductores",
        number=5,
        title="Capacitores e inductores",
        short_title="Capacitores e inductores",
        description=(
            "Explore almacenamiento de energía, continuidad de las variables de "
            "estado y respuestas transitorias de primer orden."
        ),
        reference="Boylestad · capítulos 10–11",
        icon="〽",
        topics=(
            TheoryTopic("capacitor", "Capacitancia y capacitores", "Carga, tensión y energía en el campo eléctrico.", "║"),
            TheoryTopic("inductor", "Inductancia e inductores", "Corriente, flujo y energía en el campo magnético.", "∿"),
            TheoryTopic("rc", "Respuesta transitoria RC", "Carga, descarga y constante de tiempo RC.", "C"),
            TheoryTopic("rl", "Respuesta transitoria RL", "Crecimiento, decaimiento y constante de tiempo L/R.", "L"),
            TheoryTopic("estado-permanente", "Estado permanente en CC", "Capacitor abierto, inductor en corto y condiciones iniciales.", "∞"),
        ),
    ),
    TheoryUnit(
        key="introduccion-ca",
        number=6,
        title="Introducción a corriente alternada",
        short_title="Introducción a CA",
        description=(
            "Describa señales senoidales y utilice valores eficaces, desfase, "
            "números complejos y fasores."
        ),
        reference="Boylestad · capítulos 13–14",
        icon="∿",
        topics=(
            TheoryTopic("senoide", "La señal senoidal", "Amplitud, período, frecuencia y velocidad angular.", "∿"),
            TheoryTopic("rms", "Valor eficaz (RMS)", "Compare el efecto energético de CA y CC.", "√"),
            TheoryTopic("fase", "Fase y desfase", "Interprete adelanto y atraso entre señales.", "φ"),
            TheoryTopic("complejos", "Números complejos", "Trabaje en forma rectangular y polar.", "j"),
            TheoryTopic("fasores", "Fasores", "Represente senoides mediante magnitud y ángulo.", "↗"),
        ),
    ),
    TheoryUnit(
        key="circuitos-potencia-ca",
        number=7,
        title="Circuitos y potencia en CA",
        short_title="Circuitos y potencia en CA",
        description=(
            "Analice R, L y C mediante impedancias y comprenda el intercambio de "
            "potencia activa y reactiva."
        ),
        reference="Boylestad · capítulos 15 y 19",
        icon="△",
        topics=(
            TheoryTopic("reactancia", "Reactancia e impedancia", "Respuesta de R, L y C en el dominio fasorial.", "Z"),
            TheoryTopic("rlc-serie", "Circuitos RLC en serie", "Suma fasorial, impedancia y resonancia básica.", "Σ"),
            TheoryTopic("rlc-paralelo", "Circuitos RLC en paralelo", "Admitancia y reparto fasorial de corriente.", "Y"),
            TheoryTopic("potencias-ca", "Potencias P, Q y S", "Potencia activa, reactiva, aparente y compleja.", "S"),
            TheoryTopic("factor-potencia", "Factor de potencia", "Ángulo, eficiencia de uso y corrección capacitiva.", "cos"),
        ),
    ),
)


def get_unit(unit_key: str | None) -> TheoryUnit:
    """Devuelve una unidad válida; usa la primera como alternativa segura."""

    return next((unit for unit in THEORY_UNITS if unit.key == unit_key), THEORY_UNITS[0])


def get_topic(unit: TheoryUnit, topic_key: str | None) -> TheoryTopic | None:
    """Busca un tema dentro de una unidad y evita enlaces cruzados inválidos."""

    return next((topic for topic in unit.topics if topic.key == topic_key), None)


def topic_position(unit: TheoryUnit, topic: TheoryTopic) -> int:
    """Posición basada en uno para indicadores de progreso."""

    return unit.topics.index(topic) + 1


def engineering_notation(value: float, unit: str = "") -> str:
    """Formatea magnitudes eléctricas con prefijos de ingeniería legibles."""

    magnitude = abs(value)
    if magnitude == 0:
        return f"0 {unit}".strip()
    prefixes = (
        (1e9, "G"),
        (1e6, "M"),
        (1e3, "k"),
        (1.0, ""),
        (1e-3, "m"),
        (1e-6, "µ"),
        (1e-9, "n"),
    )
    for scale, prefix in prefixes:
        if magnitude >= scale or scale == 1e-9:
            scaled = value / scale
            decimals = 0 if abs(scaled) >= 100 else 1 if abs(scaled) >= 10 else 2
            return f"{scaled:.{decimals}f} {prefix}{unit}".strip()
    return f"{value:g} {unit}".strip()
