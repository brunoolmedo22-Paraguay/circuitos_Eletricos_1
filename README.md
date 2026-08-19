# ⚡ Circuitos Eléctricos I — Plataforma de Monitoría

Plataforma modular construida con **Streamlit + Python** como complemento de la
disciplina *Circuitos Eléctricos I* (UNILA).

El proyecto no sustituye las clases. Funciona como un repositorio académico al
que el estudiante puede volver para localizar conceptos, ecuaciones,
convenciones, herramientas de cálculo y ejercicios resueltos.

> **Estado actual: Versión 0.3** — arquitectura y portada activas. El módulo
> **Aprenda la Teoría** está completamente vacío y reservado para ser reconstruido desde cero.

---

## 🎯 Visión del proyecto

La plataforma crecerá alrededor de cuatro grandes módulos:

| Módulo | Descripción |
| --- | --- |
| 📘 **Aprenda la Teoría** | Página completamente vacía, reservada para reconstruir el contenido desde cero. |
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

## 📘 Aprenda la Teoría · Versión 0.3

El módulo está completamente vacío. No contiene títulos, directorios internos, unidades, artículos, tópicos, búsqueda, gráficos, referencias ni material teórico.

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
