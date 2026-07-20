# ⚡ Circuitos Eléctricos I — Plataforma de Monitoría

Plataforma modular construida con **Streamlit + Python** como complemento de la
disciplina *Circuitos Eléctricos I* (UNILA).

El proyecto no sustituye las clases. Funciona como un repositorio académico al
que el estudiante puede volver para localizar conceptos, ecuaciones,
convenciones, herramientas de cálculo y ejercicios resueltos.

> **Estado actual: Versión 0.3** — arquitectura, portada y módulo
> **Aprenda la Teoría** convertido en una base de consulta. La primera unidad,
> *Fundamentos de circuitos en CC*, incluye siete artículos técnicos con
> referencias directas a Boylestad y herramientas interactivas opcionales.

---

## 🎯 Visión del proyecto

La plataforma crecerá alrededor de cuatro grandes módulos:

| Módulo | Descripción |
| --- | --- |
| 📘 **Aprenda la Teoría** | Repositorio teórico organizado en siete unidades, con búsqueda, fichas de referencia, ecuaciones, tablas, citas y herramientas gráficas opcionales. |
| 🎛️ **Interactúe con la Teoría** | Simulaciones dinámicas con *sliders*: Ley de Ohm, circuitos RC/RL, constante de tiempo, carga/descarga, etc. Gráficos interactivos. |
| 📐 **Formularios** | Biblioteca organizada de ecuaciones renderizadas en LaTeX. |
| ✅ **Ejercicios Resueltos** | Problemas desarrollados paso a paso con ecuaciones en LaTeX. |

---

## 🗂️ Estructura

```
Circuitos_Electricos_I/
├── app.py                 # Portada (landing)
├── requirements.txt
├── README.md
│
├── .streamlit/
│   └── config.toml        # Tema (paleta púrpura UNILA)
│
├── assets/                # Imágenes (logo e íconos de las tarjetas)
│   ├── logo_unila.png
│   ├── teoria.png
│   ├── interactue.png
│   ├── formularios.png
│   └── solutions.png
│
├── styles/
│   └── main.css           # Estilo global (paleta, tipografía, tarjetas)
│
├── utils/                 # Código reutilizable
│   ├── __init__.py
│   ├── helpers.py         # rutas, base64, config, CSS, navegación
│   └── theory.py          # catálogo de unidades y capítulos de teoría
│
└── pages/                 # Módulos (multipágina de Streamlit)
    ├── teoria.py
    ├── interactue.py
    ├── formularios.py
    └── ejercicios.py
```

Todas las rutas son **relativas**, por lo que el proyecto funciona igual en
local, en GitHub y en Streamlit Cloud.

---

## 🚀 Ejecutar en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

La app abre en `http://localhost:8501`.

## ☁️ Desplegar en Streamlit Cloud

1. Sube el repositorio a GitHub.
2. En [share.streamlit.io](https://share.streamlit.io) crea una nueva app.
3. Archivo principal: `app.py`.

---

## 🧩 Cómo agregar un módulo nuevo

La lista `SECTIONS` en `utils/helpers.py` es la **única fuente de verdad**: la
portada, la barra lateral y las páginas leen de ahí. Para sumar una sección,
agrega su entrada a `SECTIONS`, coloca su ícono en `assets/` y crea el archivo
correspondiente en `pages/`.

## 📘 Aprenda la Teoría · Versión 0.3

El módulo usa parámetros de URL (`unit` y `topic`) para que cada artículo pueda
abrirse directamente y conservarse al recargar la página. La portada incorpora
una búsqueda conceptual y un índice con las siete unidades de la disciplina;
las entradas aún no desarrolladas permanecen identificadas como contenido
pendiente.

La Unidad 1 contiene:

1. ¿Qué es un circuito eléctrico?
2. Tensión y corriente.
3. Resistencia y resistores.
4. Ley de Ohm.
5. Potencia, energía y eficiencia.
6. Consumo eléctrico.
7. Circuito abierto, cortocircuito y medición.

Cada artículo está pensado para consulta rápida después de clase: índice
interno, ficha de magnitudes, definiciones compactas, ecuaciones, tablas de
comparación, advertencias técnicas, referencias de página y navegación entre
temas. Los gráficos y calculadores permanecen disponibles dentro de paneles
desplegables, sin interrumpir la lectura principal.

### Referencia bibliográfica

La secuencia y el alcance conceptual toman como referencia:

> BOYLESTAD, Robert L. *Introdução à análise de circuitos*. 12. ed. São Paulo:
> Pearson Prentice Hall, 2012.

Los artículos incluyen citas en el texto con el formato
`(BOYLESTAD, 2012, p. xx)` y una ficha bibliográfica al final. Los textos,
ejemplos, diagramas y visualizaciones fueron redactados específicamente para
este proyecto; el libro no se redistribuye con la aplicación.

---

## 🎨 Notas de diseño

- Paleta púrpura UNILA (`#88678b` / `#532458`) definida como variables CSS.
- Tipografías **Poppins** (títulos) e **Inter** (texto).
- Tarjetas con *hover*, sombras suaves y bordes redondeados.
- Los archivos de `assets/` son **placeholders**; reemplázalos por los
  definitivos manteniendo los mismos nombres. En particular, sustituye
  `logo_unila.png` por el logotipo institucional oficial.

---

*Desarrollado por el Monitor **Bruno Manuel Olmedo Chavez** · UNILA.*
