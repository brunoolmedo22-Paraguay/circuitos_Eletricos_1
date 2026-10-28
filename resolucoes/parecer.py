"""Geração do parecer acadêmico em PDF (devolução ou aprovação).

Gerado no servidor com ReportLab (biblioteca gratuita e sem serviços externos)
e armazenado de forma persistente junto à avaliação correspondente.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import constants as C

ASSETS = Path(__file__).resolve().parent.parent / "assets"

PURPLE = colors.HexColor("#532458")
PANEL = colors.HexColor("#8b6a8f")
LAVENDER = colors.HexColor("#f3edf5")
LINE = colors.HexColor("#d9cddd")
INK = colors.HexColor("#211c26")
MUTED = colors.HexColor("#6b6472")
GREEN = colors.HexColor("#2f7d63")
AMBER = colors.HexColor("#9a5b17")
RED = colors.HexColor("#a23b3b")


def _p(text: str | None) -> str:
    return escape(text or "").replace("\n", "<br/>")


def _fmt(dt: datetime | None, tz=None) -> str:
    if not dt:
        return "—"
    if tz is not None:
        from datetime import timezone

        dt = dt.replace(tzinfo=timezone.utc).astimezone(tz)
    return dt.strftime("%d/%m/%Y %H:%M")


def build_parecer_pdf(data: dict, *, tz=None) -> bytes:
    """Monta o PDF. ``data`` vem de ``ReviewService._parecer_payload``."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=36 * mm,
        bottomMargin=20 * mm,
        title=f"Parecer — Exercício {data['exercise_code']}",
        author=data.get("institution", "UNILA"),
        subject="Parecer acadêmico — Circuitos Elétricos I",
    )

    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.6, leading=13.4, textColor=INK)
    small = ParagraphStyle("small", parent=body, fontSize=8.2, leading=11, textColor=MUTED)
    label = ParagraphStyle("label", parent=body, fontName="Helvetica-Bold", fontSize=7.6, leading=10, textColor=PANEL)
    h2 = ParagraphStyle(
        "h2", parent=body, fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=PURPLE, spaceBefore=8, spaceAfter=4
    )
    cell = ParagraphStyle("cell", parent=body, fontSize=8.8, leading=11.6, alignment=TA_LEFT)
    cell_b = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")

    approved = data["decision"] == C.DECISION_APROVADA
    status_text = C.LEVEL_LABELS.get(data.get("level"), "Aprovado") if approved else C.DEVOLVIDO_LABEL
    status_color = GREEN if approved else AMBER
    doc_title = "Parecer de Aprovação" if approved else "Parecer de Devolução para Correção"

    story: list = []

    # ---- Identificação -------------------------------------------------- #
    story.append(Paragraph(doc_title, ParagraphStyle("t", parent=h2, fontSize=16, leading=20, spaceBefore=0)))
    story.append(
        Paragraph(
            f"Exercício {_p(data['exercise_code'])} — {_p(data['exercise_title'])}",
            ParagraphStyle("st", parent=body, fontSize=11, leading=15, textColor=INK, fontName="Helvetica-Bold"),
        )
    )
    story.append(Spacer(1, 5 * mm))

    status_tbl = Table(
        [[Paragraph(f"<font color='white'><b>{_p(status_text.upper())}</b></font>", body)]],
        colWidths=[doc.width],
    )
    status_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), status_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(status_tbl)
    story.append(Spacer(1, 4 * mm))

    def kv(k, v):
        return [Paragraph(k.upper(), label), Paragraph(_p(v), cell)]

    ident = [
        kv("Disciplina", data.get("course", "Circuitos Elétricos I")),
        kv("Instituição", data.get("institution", "")),
        kv("Estudante", data["student_name"] + (f" (matrícula {data['student_matricula']})" if data.get("student_matricula") else "")),
    ]
    if data.get("coauthors"):
        ident.append(kv("Coautoria", data["coauthors"]))
    ident += [
        kv("Unidade / tema", data.get("unit") or "—"),
        kv("Versão avaliada", f"v{data['version_no']}"),
        kv("Data de envio", _fmt(data.get("submitted_at"), tz)),
        kv("Data da avaliação", _fmt(data.get("reviewed_at"), tz)),
        kv("Avaliador(a)", data["reviewer_name"]),
    ]
    t = Table(ident, colWidths=[38 * mm, doc.width - 38 * mm])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(t)

    # ---- Requisitos ------------------------------------------------------ #
    story.append(Paragraph("Requisitos obrigatórios", h2))
    reqs = data.get("requirements", {})
    rows = [[Paragraph("Material", cell_b), Paragraph("Situação", cell_b)]]
    for key, name in C.REQUIREMENTS:
        ok = bool(reqs.get(key))
        rows.append(
            [
                Paragraph(name, cell),
                Paragraph(
                    f"<font color='{'#2f7d63' if ok else '#a23b3b'}'><b>{'Cumprido' if ok else 'Não cumprido'}</b></font>",
                    cell,
                ),
            ]
        )
    t = Table(rows, colWidths=[doc.width * 0.7, doc.width * 0.3])
    t.setStyle(_grid_style())
    story.append(t)

    # ---- Critérios ------------------------------------------------------- #
    story.append(Paragraph("Avaliação qualitativa por critério", h2))
    crit = data.get("criteria", {})
    rows = [[Paragraph("Critério", cell_b), Paragraph("Avaliação", cell_b), Paragraph("Comentário", cell_b)]]
    for key, name in C.CRITERIA:
        item = crit.get(key) or {}
        rating = item.get("rating")
        color = {"atende": "#2f7d63", "parcial": "#9a5b17", "nao_atende": "#a23b3b"}.get(rating, "#6b6472")
        rows.append(
            [
                Paragraph(name, cell),
                Paragraph(f"<font color='{color}'><b>{_p(C.RATINGS.get(rating, '—'))}</b></font>", cell),
                Paragraph(_p(item.get("comment") or "—"), cell),
            ]
        )
    t = Table(rows, colWidths=[doc.width * 0.38, doc.width * 0.2, doc.width * 0.42], repeatRows=1)
    t.setStyle(_grid_style())
    story.append(t)

    # ---- Texto livre ----------------------------------------------------- #
    sections = []
    if not approved:
        sections.append(("Problemas identificados", data.get("problems")))
    sections.append(("Observações técnicas e didáticas", data.get("observations")))
    sections.append(("Recomendações", data.get("recommendations")))
    if not approved:
        sections.append(("Indicações para o reenvio", data.get("resubmit_instructions") or _default_resubmit()))
    for title, text in sections:
        if text and text.strip():
            story.append(KeepTogether([Paragraph(title, h2), Paragraph(_p(text), body)]))

    # ---- Materiais avaliados -------------------------------------------- #
    story.append(Paragraph("Materiais avaliados", h2))
    mats = [
        kv("Vídeo", data.get("youtube_url") or "—"),
        kv("PDF", data.get("pdf_filename") or "—"),
        kv("Falstad", _shorten(data.get("falstad_url") or "—", 110)),
    ]
    t = Table(mats, colWidths=[38 * mm, doc.width - 38 * mm])
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t)

    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            "Este parecer registra uma avaliação qualitativa. A plataforma não atribui notas, pontos ou "
            "porcentagens; a eventual conversão em nota da disciplina é de responsabilidade exclusiva do professor.",
            small,
        )
    )

    footer_id = data.get("review_id", "")[:8].upper()
    logo_path = ASSETS / "logo_unila.png"

    def on_page(canvas, _doc):
        canvas.saveState()
        w, h = A4
        canvas.setFillColor(PURPLE)
        canvas.rect(0, h - 26 * mm, w, 26 * mm, stroke=0, fill=1)
        canvas.setFillColor(PANEL)
        canvas.rect(0, h - 27.6 * mm, w, 1.6 * mm, stroke=0, fill=1)
        x = 18 * mm
        if logo_path.exists():
            try:
                # Logo sobre um cartão branco para manter as cores institucionais.
                canvas.setFillColor(colors.white)
                canvas.roundRect(x - 2 * mm, h - 22.5 * mm, 46 * mm, 17 * mm, 2.5 * mm, stroke=0, fill=1)
                canvas.drawImage(
                    str(logo_path), x, h - 21 * mm, width=42 * mm, height=14 * mm, preserveAspectRatio=True, mask="auto"
                )
                x += 52 * mm
            except Exception:
                pass
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(x, h - 12.5 * mm, data.get("course", "Circuitos Elétricos I"))
        canvas.setFont("Helvetica", 8.6)
        canvas.drawString(x, h - 17.5 * mm, "Exercícios Resolvidos · Parecer acadêmico")
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.4)
        canvas.drawString(18 * mm, 10 * mm, f"Parecer nº {footer_id} · gerado pela plataforma Circuitos Elétricos I — UNILA")
        canvas.drawRightString(w - 18 * mm, 10 * mm, f"Página {_doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


def _grid_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), LAVENDER),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _shorten(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 3] + "..."


def _default_resubmit() -> str:
    return (
        "Acesse a plataforma, abra “Alterar Resolução” e use “Preparar nova versão”. Corrija os pontos "
        "indicados neste parecer, atualize os materiais necessários (vídeo, PDF e/ou circuito Falstad) "
        "e envie novamente para avaliação. A versão anterior e este parecer permanecem no histórico."
    )
