"""Peças visuais reutilizáveis (HTML escapado + componentes Streamlit)."""

from __future__ import annotations

import html
from urllib.parse import quote

import streamlit as st

from .. import constants as C
from ..validators import format_duration, thumbnail_url

esc = html.escape


def md(html_text: str) -> None:
    """Injeta HTML (sem indentação, para não virar bloco de código no Markdown)."""
    cleaned = "\n".join(line.strip() for line in html_text.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


STATUS_TONE = {
    C.RASCUNHO: "neutral",
    C.SUBMETIDA: "info",
    C.REENVIADA: "info",
    C.EM_ANALISE: "progress",
    C.DEVOLVIDA: "warn",
    C.APROVADA: "ok",
    C.RETIRADA: "muted",
}
LEVEL_TONE = {C.EXCELENTE: "lvl-exc", C.MUITO_BOM: "lvl-mb", C.BOM: "lvl-bom"}


def status_badge(status: str) -> str:
    return f'<span class="ex-badge ex-badge--{STATUS_TONE.get(status, "neutral")}">{esc(C.STATUS_LABELS.get(status, status))}</span>'


def level_badge(level: str | None, *, long: bool = False) -> str:
    if not level:
        return ""
    text = C.LEVEL_LABELS[level] if long else C.LEVEL_SHORT[level]
    return f'<span class="ex-level {LEVEL_TONE.get(level, "")}"><i></i>{esc(text)}</span>'


def thumb_html(video_id: str | None, *, duration_s: int | None = None, extra_chip: str = "", alt: str = "") -> str:
    """Miniatura 16:9. Se a imagem do YouTube falhar, o gradiente de fundo aparece."""
    bg = f"url('{thumbnail_url(video_id)}'), " if video_id else ""
    dur = f'<span class="ex-thumb__dur">{esc(format_duration(duration_s))}</span>' if duration_s else ""
    chip = f'<span class="ex-thumb__chip">{esc(extra_chip)}</span>' if extra_chip else ""
    return (
        f'<div class="ex-thumb" role="img" aria-label="{esc(alt)}" '
        f'style="background-image:{bg}linear-gradient(140deg,#8b6a8f 0%,#532458 100%);">'
        f'<span class="ex-thumb__play" aria-hidden="true"></span>{chip}{dur}</div>'
    )


def section_head(kicker: str, title: str, subtitle: str = "", count: int | None = None) -> None:
    count_html = f'<div class="ex-head__count">{count}</div>' if count is not None else ""
    md(
        f"""
        <div class="ex-head">
          <div>
            <div class="ex-head__kicker">{esc(kicker)}</div>
            <h2>{esc(title)}</h2>
            {f'<p>{esc(subtitle)}</p>' if subtitle else ''}
          </div>
          {count_html}
        </div>
        """
    )


def empty_state(title: str, text: str, icon: str = "◎") -> None:
    md(
        f"""
        <div class="ex-empty">
          <div class="ex-empty__icon" aria-hidden="true">{esc(icon)}</div>
          <h3>{esc(title)}</h3>
          <p>{esc(text)}</p>
        </div>
        """
    )


def chips(items: list[str]) -> str:
    return "".join(f'<span class="ex-chip">{esc(t)}</span>' for t in items if t)


def whatsapp_link(message: str, phone: str | None = None) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    base = f"https://wa.me/{digits}" if digits else "https://wa.me/"
    return f"{base}?text={quote(message)}"


def youtube_embed(video_id: str, height: int = 400) -> None:
    from ..validators import embed_url

    md(
        f"""
        <div class="ex-video">
          <iframe src="{esc(embed_url(video_id))}" title="Vídeo da resolução"
            allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            referrerpolicy="strict-origin-when-cross-origin" allowfullscreen loading="lazy"></iframe>
        </div>
        """
    )


@st.cache_data(show_spinner=False, max_entries=200, ttl=3600)
def render_pdf_page(data: bytes, page: int, scale: float = 1.5) -> bytes | None:
    """Converte uma página do PDF em PNG para pré-visualização (funciona também no celular)."""
    try:
        import io

        import pypdfium2 as pdfium

        doc = pdfium.PdfDocument(data)
        if page >= len(doc):
            return None
        img = doc[page].render(scale=scale).to_pil()
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except Exception:
        return None


def pdf_page_count(data: bytes) -> int:
    try:
        import pypdfium2 as pdfium

        return len(pdfium.PdfDocument(data))
    except Exception:
        return 0


def pdf_preview(data: bytes, key: str) -> None:
    n = pdf_page_count(data)
    if n == 0:
        st.warning("Não foi possível gerar a pré-visualização deste PDF. Use o botão de download.")
        return
    page = 1
    if n > 1:
        page = st.select_slider("Página", options=list(range(1, n + 1)), value=1, key=f"pdfpg-{key}",
                                format_func=lambda i: f"{i} de {n}")
    png = render_pdf_page(data, page - 1)
    if png:
        st.image(png, use_container_width=True)
    else:
        st.warning("Página indisponível para pré-visualização.")
