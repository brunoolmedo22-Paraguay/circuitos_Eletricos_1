# ⚡ Circuitos Eléctricos I — Guía Interactiva de Aprendizaje

Plataforma educativa modular construida con **Streamlit + Python** como
complemento oficial de la disciplina *Circuitos Eléctricos I* (UNILA).

El objetivo es acompañar el proceso de aprendizaje del alumno siguiendo una
secuencia lógica similar a la del semestre: aprender la teoría, interactuar con
ella, consultar formularios y estudiar ejercicios resueltos.

> **Estado actual: Versión 0.1** — arquitectura del proyecto y portada
> profesional. Los módulos de contenido se desarrollan por versiones.

---

## 🎯 Visión del proyecto

La plataforma crecerá alrededor de cuatro grandes módulos:

| Módulo | Descripción |
| --- | --- |
| 📘 **Aprenda la Teoría** | Contenidos teóricos: Ley de Ohm, potencia, energía, Kirchhoff, resistencias, divisores, Thévenin, Norton, capacitores, inductores, RC y RL. Cada tema con explicación, imágenes, ejemplos, ecuaciones en LaTeX y observaciones. |
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
│   └── helpers.py         # rutas, base64, config, CSS, navegación
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
