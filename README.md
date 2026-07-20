# ⚡ Circuitos Eléctricos I — Guía Interactiva de Aprendizaje

Plataforma educativa modular construida con **Streamlit + Python** como
complemento oficial de la disciplina *Circuitos Eléctricos I* (UNILA).

El objetivo es acompañar el proceso de aprendizaje del alumno siguiendo una
secuencia lógica similar a la del semestre: aprender la teoría, interactuar con
ella, consultar formularios y estudiar ejercicios resueltos.

> **Estado actual: Versión 0.2** — arquitectura, portada y módulo
> **Aprenda la Teoría** con siete unidades organizadas. La primera unidad,
> *Fundamentos de circuitos en CC*, incluye siete capítulos interactivos.

---

## 🎯 Visión del proyecto

La plataforma crecerá alrededor de cuatro grandes módulos:

| Módulo | Descripción |
| --- | --- |
| 📘 **Aprenda la Teoría** | Libro digital organizado en siete unidades. La Unidad 1 ya incluye circuito eléctrico, tensión, corriente, resistencia, Ley de Ohm, potencia, energía, consumo y medición, con ecuaciones, ejemplos y gráficos interactivos. |
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

## 📘 Aprenda la Teoría · Versión 0.2

El módulo usa parámetros de URL (`unit` y `topic`) para que cada capítulo pueda
abrirse directamente y conservarse al recargar la página. La biblioteca muestra
las siete unidades de la disciplina y marca como **Próximamente** los capítulos
que todavía no fueron desarrollados.

La Unidad 1 contiene:

1. ¿Qué es un circuito eléctrico?
2. Tensión y corriente.
3. Resistencia y resistores.
4. Ley de Ohm.
5. Potencia, energía y eficiencia.
6. Consumo eléctrico.
7. Circuito abierto, cortocircuito y medición.

Cada capítulo mantiene la misma estructura didáctica: objetivos, explicación,
ecuaciones, experiencia guiada, error frecuente, comprobación rápida, resumen y
navegación anterior/siguiente.

### Referencia didáctica

La secuencia y el alcance conceptual toman como referencia:

> BOYLESTAD, Robert L. *Introdução à análise de circuitos*. 12. ed. São Paulo:
> Pearson Prentice Hall, 2012.

Los textos, ejemplos, diagramas y visualizaciones de la plataforma fueron
redactados específicamente para este proyecto; el libro no se redistribuye con
la aplicación.

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
