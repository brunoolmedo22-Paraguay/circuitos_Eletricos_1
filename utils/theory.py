"""Catálogo y utilidades del repositorio ``Aprenda la Teoría``.

El catálogo vive fuera de la página para mantener una única estructura de
consulta. Los artículos son originales y utilizan Boylestad (12.ª edición)
como referencia bibliográfica de secuencia y alcance.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TheoryTopic:
    """Metadatos de una entrada de consulta dentro de una unidad."""

    key: str
    title: str
    description: str
    icon: str
    source_pages: str = ""
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
            "Definiciones y relaciones básicas: circuito eléctrico, tensión, "
            "corriente, resistencia, Ley de Ohm, potencia, energía y consumo."
        ),
        reference="Boylestad · capítulos 2–4",
        icon="⚡",
        topics=(
            TheoryTopic(
                "que-es-un-circuito",
                "¿Qué es un circuito eléctrico?",
                "Estructura mínima, elementos funcionales y estados del circuito.",
                "🔌",
                "pp. 29–30",
                True,
            ),
            TheoryTopic(
                "tension-y-corriente",
                "Tensión y corriente",
                "Definiciones, unidades, relaciones y sentidos de referencia.",
                "↗",
                "pp. 27–30",
                True,
            ),
            TheoryTopic(
                "resistencia",
                "Resistencia y resistores",
                "Resistividad, geometría, conductancia y código de colores.",
                "〰",
                "pp. 51–52, 64–67",
                True,
            ),
            TheoryTopic(
                "ley-de-ohm",
                "Ley de Ohm",
                "Relaciones entre V, I y R e interpretación de la característica V–I.",
                "Ω",
                "pp. 84–87",
                True,
            ),
            TheoryTopic(
                "potencia-y-energia",
                "Potencia, energía y eficiencia",
                "Definiciones, unidades, ecuaciones de potencia y rendimiento.",
                "💡",
                "pp. 89–94",
                True,
            ),
            TheoryTopic(
                "consumo-electrico",
                "Consumo eléctrico",
                "Diferencia entre kW y kWh, medición, energía y costo básico.",
                "🧾",
                "pp. 91–94",
                True,
            ),
            TheoryTopic(
                "abierto-corto-medicion",
                "Circuito abierto, corto y medición",
                "Modelos abierto y corto; conexión de amperímetro y voltímetro.",
                "🧰",
                "pp. 42–43, 179–180",
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
            "Asociaciones serie, paralelo y serie–paralelo; resistencia "
            "equivalente y leyes de Kirchhoff."
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
            "Métodos para redes que no pueden reducirse únicamente mediante "
            "asociaciones serie–paralelo."
        ),
        reference="Boylestad · capítulo 8 + ampliación didáctica",
        icon="🧠",
        topics=(
            TheoryTopic("topologia", "Ramas, nodos y mallas", "Topología de la red y recuento de variables.", "◫"),
            TheoryTopic("nodal", "Análisis nodal", "Tensiones desconocidas y formulación mediante KCL.", "●"),
            TheoryTopic("supernodos", "Supernodos", "Fuentes de tensión entre dos nodos no conocidos.", "◉"),
            TheoryTopic("mallas", "Análisis de mallas", "Corrientes desconocidas y formulación mediante KVL.", "↻"),
            TheoryTopic("supermallas", "Supermallas", "Fuentes de corriente compartidas entre mallas.", "◎"),
        ),
    ),
    TheoryUnit(
        key="teoremas",
        number=4,
        title="Teoremas de circuitos",
        short_title="Teoremas de circuitos",
        description=(
            "Equivalentes y principios para representar una red y estudiar su "
            "efecto sobre una carga."
        ),
        reference="Boylestad · capítulo 9",
        icon="🧩",
        topics=(
            TheoryTopic("superposicion", "Superposición", "Contribución individual de cada fuente independiente.", "+"),
            TheoryTopic("thevenin", "Teorema de Thévenin", "Equivalente con fuente de tensión y resistencia en serie.", "T"),
            TheoryTopic("norton", "Teorema de Norton", "Equivalente con fuente de corriente y resistencia en paralelo.", "N"),
            TheoryTopic("maxima-potencia", "Máxima transferencia de potencia", "Condición de carga para la máxima potencia recibida.", "P"),
        ),
    ),
    TheoryUnit(
        key="capacitores-inductores",
        number=5,
        title="Capacitores e inductores",
        short_title="Capacitores e inductores",
        description=(
            "Almacenamiento de energía, continuidad de las variables de estado "
            "y respuestas transitorias de primer orden."
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
            "Señales senoidales, valores eficaces, desfase, números complejos y "
            "representación fasorial."
        ),
        reference="Boylestad · capítulos 13–14",
        icon="∿",
        topics=(
            TheoryTopic("senoide", "La señal senoidal", "Amplitud, período, frecuencia y velocidad angular.", "∿"),
            TheoryTopic("rms", "Valor eficaz (RMS)", "Equivalencia energética entre magnitudes de CA y CC.", "√"),
            TheoryTopic("fase", "Fase y desfase", "Adelanto y atraso entre señales senoidales.", "φ"),
            TheoryTopic("complejos", "Números complejos", "Formas rectangular y polar; operaciones básicas.", "j"),
            TheoryTopic("fasores", "Fasores", "Representación de senoides mediante magnitud y ángulo.", "↗"),
        ),
    ),
    TheoryUnit(
        key="circuitos-potencia-ca",
        number=7,
        title="Circuitos y potencia en CA",
        short_title="Circuitos y potencia en CA",
        description=(
            "Modelos de R, L y C mediante impedancias; potencia activa, reactiva "
            "y aparente."
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
