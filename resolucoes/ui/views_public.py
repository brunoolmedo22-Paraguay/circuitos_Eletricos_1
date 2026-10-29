"""Catálogo público e página individual de cada resolução."""

from __future__ import annotations

import streamlit as st

from .. import constants as C
from ..errors import AppError
from ..services import Platform, User
from ..services.catalog import SORT_OPTIONS, filter_items, group_by_exercise
from ..validators import format_duration, watch_url
from .runtime import get_platform, nav_to
from .widgets import chips, empty_state, esc, level_badge, md, pdf_preview, section_head, thumb_html, youtube_embed


# --------------------------------------------------------------------------- #
# Dados em cache (somente conteúdo público)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=60, show_spinner=False)
def published_items() -> list[dict]:
    return get_platform().catalog.published()


@st.cache_data(ttl=600, max_entries=30, show_spinner=False)
def public_pdf(version_id: str) -> tuple[bytes, str]:
    # actor=None: o serviço só entrega se a versão estiver publicada.
    return get_platform().submissions.version_pdf(None, version_id)


def clear_public_cache() -> None:
    published_items.clear()
    public_pdf.clear()


def _hero(count_ex: int, count_res: int) -> None:
    from utils import data_uri

    icon = data_uri("exercicios.png")
    stats = (
        f'<div class="ex-hero__stats"><span><strong>{count_ex}</strong> exercícios</span>'
        f'<span><strong>{count_res}</strong> resoluções aprovadas</span></div>'
        if count_res
        else ""
    )
    md(
        f"""
        <div class="page-hero ex-hero">
          <div class="page-hero__badge">{f'<img src="{icon}" alt="" />' if icon else '✅'}</div>
          <div class="page-hero__text">
            <span class="eyebrow">Biblioteca colaborativa</span>
            <h1>Exercícios Resolvidos</h1>
            <p>Resoluções feitas por estudantes e verificadas pela equipe da disciplina.
            Estude cada exercício pelo vídeo, pelo PDF ou pela simulação no Falstad.</p>
            {stats}
          </div>
        </div>
        """
    )


# --------------------------------------------------------------------------- #
# Catálogo
# --------------------------------------------------------------------------- #
def _reset_filters() -> None:
    for k in ("cat_q", "cat_units", "cat_levels"):
        st.session_state.pop(k, None)


def catalog(p: Platform, user: User | None) -> None:
    items = published_items()
    groups_all = group_by_exercise(items)
    _hero(len(groups_all), len(items))

    if not items:
        empty_state(
            "A biblioteca ainda não tem resoluções aprovadas",
            "As resoluções aparecem aqui assim que a equipe da disciplina aprova uma entrega. "
            "Escolha um exercício proposto e seja o primeiro a publicar.",
            "▶",
        )
        c = st.columns([1, 1, 1])[1]
        with c:
            if user and user.is_student:
                st.button("Ver Exercícios Propostos", type="primary", use_container_width=True,
                          on_click=nav_to, args=("propostos",))
            elif not user:
                st.button("Entrar para submeter", type="primary", use_container_width=True,
                          on_click=nav_to, args=("entrar",), kwargs={"next": "propostos"})
        return

    units = sorted({i["unit"] for i in items if i["unit"]})
    with st.container(key="ex-filters"):
        f1, f2, f3, f4 = st.columns([3.2, 2.2, 2, 1.8])
        q = f1.text_input("Buscar", key="cat_q", placeholder="Número, título, tema ou conceito (ex.: 2.04, Thévenin)")
        sel_units = f2.multiselect("Unidade", units, key="cat_units", placeholder="Todas")
        sel_levels = f3.multiselect("Nível", list(C.LEVELS), key="cat_levels", placeholder="Todos",
                                    format_func=lambda lv: C.LEVEL_SHORT[lv])
        sort = f4.selectbox("Ordenar por", list(SORT_OPTIONS), format_func=SORT_OPTIONS.get, key="cat_sort")

    filtered = filter_items(items, q=q, units=sel_units, levels=sel_levels)
    groups = group_by_exercise(filtered, sort=sort)
    filtering = bool(q or sel_units or sel_levels)
    section_head(
        "Resultados" if filtering else "Biblioteca",
        f"{len(groups)} exercício{'s' if len(groups) != 1 else ''} resolvido{'s' if len(groups) != 1 else ''}",
        "Cada cartão reúne as resoluções aprovadas de um exercício; a de melhor nível aparece em destaque.",
    )
    if not groups:
        empty_state("Nenhuma resolução encontrada", "Tente outro termo de busca ou remova algum filtro.", "⌕")
        st.columns([1, 1, 1])[1].button("Limpar filtros", use_container_width=True, on_click=_reset_filters)
        return

    per_row = 3
    for start in range(0, len(groups), per_row):
        cols = st.columns(per_row, gap="medium")
        for col, g in zip(cols, groups[start:start + per_row]):
            f = g["featured"]
            n = len(g["resolutions"])
            others = f" e mais {n - 1}" if n > 1 else ""
            with col, st.container(key=f"ex-card-{g['exercise_id']}"):
                md(
                    thumb_html(f["youtube_id"], duration_s=f["video_duration_s"],
                               extra_chip=f"{n} resoluções" if n > 1 else "",
                               alt=f"Miniatura do vídeo do exercício {g['code']}")
                    + f"""
                    <div class="ex-card__body">
                      <div class="ex-card__code">Exercício {esc(g['code'])}</div>
                      <div class="ex-card__title">{esc(g['title'])}</div>
                      <div class="ex-card__unit">{esc(g['unit'])}</div>
                      <div class="ex-card__meta">
                        <span class="ex-card__author">{esc(f['author_name'])}{esc(others)}</span>
                        {level_badge(f['level'])}
                      </div>
                    </div>
                    """
                )
                st.button("Estudar resolução", key=f"open-{f['submission_id']}", use_container_width=True,
                          on_click=nav_to, args=("resolucao",), kwargs={"r": f["submission_id"]})


# --------------------------------------------------------------------------- #
# Página da resolução
# --------------------------------------------------------------------------- #
def detail(p: Platform, user: User | None, sid: str | None) -> None:
    st.button("← Voltar à biblioteca", key="back-cat", on_click=nav_to, args=(None,))
    item = p.catalog.get(sid) if sid else None
    if item is None:
        empty_state(
            "Resolução não disponível",
            "Ela pode ter sido retirada da biblioteca ou o link está incompleto.",
            "∅",
        )
        return

    coaut = f" · com {item['coauthors']}" if item["coauthors"] else ""
    md(
        f"""
        <header class="ex-detail-head">
          <div class="ex-detail-head__kicker">{esc(item['unit'])}</div>
          <h1>Exercício {esc(item['code'])} — {esc(item['title'])}</h1>
          <div class="ex-detail-head__meta">
            {level_badge(item['level'], long=True)}
            <span>Resolução de <strong>{esc(item['author_name'])}</strong>{esc(coaut)}</span>
            <span>Aprovada em {esc(p.fmt(item['published_at'], with_time=False))}</span>
            <span>Versão v{item['version_no']}</span>
          </div>
          <div class="ex-detail-head__chips">{chips(item['topic_list'])}</div>
        </header>
        """
    )
    if item["resource_alert"]:
        st.warning(f"Alguns materiais podem estar indisponíveis no momento ({item['resource_alert']}). "
                   "A equipe da disciplina já foi sinalizada.")

    with st.container(key="ex-statement"):
        from .exercise_view import render_exercise

        render_exercise(p, p.exercises.get(item["exercise_id"]), key=f"pub-{item['submission_id']}")

    section_head("Três formas de estudar", "Escolha como estudar esta resolução",
                 "Não há ordem obrigatória: assista, leia ou experimente o circuito.")

    left, right = st.columns([1.75, 1], gap="medium")
    with left, st.container(key="ex-res-video"):
        dur = format_duration(item["video_duration_s"])
        md(f'<div class="ex-res__title"><span class="ex-res__n">1</span>Vídeo da Resolução'
           f'{f"<span class=ex-res__aside>{esc(dur)}</span>" if dur else ""}</div>')
        youtube_embed(item["youtube_id"])
        st.link_button("Abrir no YouTube", watch_url(item["youtube_id"]), icon=":material/open_in_new:")
        st.caption("Se o vídeo não carregar aqui (por exemplo, incorporação bloqueada), abra-o diretamente no YouTube.")

    with right:
        with st.container(key="ex-res-pdf"):
            pages = f"{item['pdf_pages']} página{'s' if (item['pdf_pages'] or 0) != 1 else ''}" if item["pdf_pages"] else ""
            md(f'<div class="ex-res__title"><span class="ex-res__n">2</span>Resolução em PDF</div>'
               f'<p class="ex-res__text">Desenvolvimento matemático e conceitual completo. {esc(pages)}</p>')
            pdf = None
            try:
                pdf, fname = public_pdf(item["version_id"])
            except AppError as exc:
                st.error(exc.message)
            if pdf:
                show = st.toggle("Visualizar PDF", key=f"pv-{item['version_id']}")
                st.download_button("Baixar PDF", pdf, file_name=fname, mime="application/pdf",
                                   icon=":material/download:", use_container_width=True, key=f"dl-{item['version_id']}")
        with st.container(key="ex-res-falstad"):
            md('<div class="ex-res__title"><span class="ex-res__n">3</span>Simulação no Falstad</div>'
               '<p class="ex-res__text">Abra o circuito montado pelo autor, altere valores e observe o comportamento.</p>')
            st.link_button("Abrir Circuito no Falstad", item["falstad_url"], type="primary",
                           icon=":material/electrical_services:", use_container_width=True)

    if pdf and st.session_state.get(f"pv-{item['version_id']}"):
        with st.container(key="ex-pdf-preview"):
            md('<div class="ex-panel__label">Pré-visualização do PDF</div>')
            pdf_preview(pdf, item["version_id"])

    others = [r for r in p.catalog.for_exercise(item["exercise_id"]) if r["submission_id"] != item["submission_id"]]
    if others:
        section_head("Mesmo exercício", "Outras resoluções aprovadas",
                     "Diferentes caminhos para o mesmo problema.", count=len(others))
        cols = st.columns(min(3, len(others)), gap="medium")
        for i, r in enumerate(others):
            with cols[i % len(cols)], st.container(key=f"ex-other-{r['submission_id']}"):
                md(thumb_html(r["youtube_id"], duration_s=r["video_duration_s"])
                   + f'<div class="ex-card__body"><div class="ex-card__meta">'
                     f'<span class="ex-card__author">{esc(r["author_name"])}</span>{level_badge(r["level"])}</div></div>')
                st.button("Ver esta resolução", key=f"oth-{r['submission_id']}", use_container_width=True,
                          on_click=nav_to, args=("resolucao",), kwargs={"r": r["submission_id"]})
