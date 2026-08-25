"""Renderização dos microexperimentos HTML/CSS/JS dentro do Streamlit.

Cada experimento vive em uma pasta própria com três arquivos:
``<nome>.html``, ``<nome>.css`` e ``<nome>.js``. O renderer apenas reúne esses
arquivos em um documento autocontido e o entrega ao iframe do Streamlit.

A estrutura deixa o módulo pronto para receber novos experimentos sem inflar
``pages/interaja.py``.
"""

from __future__ import annotations

from pathlib import Path

import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent


def _build_document(name: str) -> str:
    folder = ROOT / name
    html_path = folder / f"{name}.html"
    css_path = folder / f"{name}.css"
    js_path = folder / f"{name}.js"

    missing = [p.name for p in (html_path, css_path, js_path) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            f"Experimento '{name}' incompleto. Arquivo(s) ausente(s): {', '.join(missing)}"
        )

    html = html_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    js = js_path.read_text(encoding="utf-8")

    return html.replace("{{EXPERIMENT_CSS}}", css).replace("{{EXPERIMENT_JS}}", js)


def render_experiment(name: str, *, height: int = 840) -> None:
    """Exibe um microexperimento autocontido."""
    components.html(_build_document(name), height=height, scrolling=False)
