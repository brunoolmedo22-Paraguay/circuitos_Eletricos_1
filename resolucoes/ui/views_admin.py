"""Administração: bandeja de revisão, avaliação, exercícios, usuários, logs e configurações."""

from __future__ import annotations

import json
from datetime import datetime, time, timedelta, timezone

import pandas as pd
import streamlit as st

from .. import constants as C
from ..errors import AppError
from ..services import Platform, User
from ..services.admin import to_csv
from ..validators import format_duration, watch_url
from .runtime import flash, go, nav_to, run_action
from .views_public import clear_public_cache
from .views_student import lazy_download, review_block
from .widgets import esc, level_badge, md, pdf_preview, section_head, status_badge, whatsapp_link, youtube_embed

SECTIONS = [
    ("bandeja", "Aprovar Resoluções"),
    ("publicacoes", "Publicações"),
    ("exercicios", "Gerenciar Exercícios"),
    ("usuarios_novo", "Adicionar Usuários"),
    ("usuarios", "Gerenciar Usuários"),
    ("log_usuarios", "Log de Usuários"),
    ("log_submissoes", "Log de Submissões"),
    ("historico", "Histórico de Avaliações"),
    ("config", "Configurações"),
]


def shell(p: Platform, user: User, section: str, item_id: str | None) -> None:
    if not st.session_state.get("_admin_logged"):
        p.users.log_admin_access(user, dict(SECTIONS).get(section, section))
        st.session_state["_admin_logged"] = True
    nav, body = st.columns([1.25, 5.2], gap="medium")
    with nav, st.container(key="ex-admin-nav"):
        md('<div class="ex-admin-nav__title">Administração</div>')
        counts = p.reviews.counts(user)
        pending = sum(counts.get(s, 0) for s in C.PENDING_STATUSES)
        for sec, label in SECTIONS:
            text = f"{label} ({pending})" if sec == "bandeja" and pending else label
            active = sec == section or (section == "avaliar" and sec == "bandeja")
            st.button(text, key=f"adm-nav-{sec}", use_container_width=True, type="primary" if active else "secondary",
                      on_click=nav_to, args=("admin",), kwargs={"a": sec})
    with body:
        {
            "bandeja": lambda: inbox(p, user),
            "avaliar": lambda: evaluate(p, user, item_id),
            "publicacoes": lambda: publications(p, user),
            "exercicios": lambda: exercises(p, user),
            "usuarios_novo": lambda: add_users(p, user),
            "usuarios": lambda: manage_users(p, user),
            "log_usuarios": lambda: logs(p, user, [C.LOG_USUARIO], "Log de Usuários"),
            "log_submissoes": lambda: logs(p, user, [C.LOG_SUBMISSAO, C.LOG_EXERCICIO], "Log de Submissões"),
            "historico": lambda: history(p, user),
            "config": lambda: config(p, user),
        }.get(section, lambda: inbox(p, user))()


def _date_range(key: str):
    rng = st.date_input("Período de envio", value=(), key=key, format="DD/MM/YYYY")
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        # Datas em horário de Brasília → UTC
        start = datetime.combine(rng[0], time.min) + timedelta(hours=3)
        end = datetime.combine(rng[1], time.max) + timedelta(hours=3)
        return start, end
    return None, None


# --------------------------------------------------------------------------- #
# Bandeja de revisão
# --------------------------------------------------------------------------- #
def inbox(p: Platform, user: User) -> None:
    counts = p.reviews.counts(user)
    section_head("Aprovar Resoluções", "Bandeja de revisão", "Entregas mais antigas primeiro.")
    tiles = [(s, counts.get(s, 0)) for s in (C.SUBMETIDA, C.REENVIADA, C.EM_ANALISE, C.DEVOLVIDA, C.APROVADA, C.RETIRADA)]
    md('<div class="ex-tiles">' + "".join(
        f'<div class="ex-tile"><span class="ex-tile__n">{n}</span>{status_badge(s)}</div>' for s, n in tiles) + "</div>")

    exs = p.exercises.list(user, include_inactive=True)
    admins = p.users.list(user, role=C.ROLE_ADMIN)
    with st.container(key="ex-filters"):
        f1, f2, f3 = st.columns(3)
        statuses = f1.multiselect("Estado", list(C.STATUS_LABELS), default=[C.SUBMETIDA, C.REENVIADA, C.EM_ANALISE],
                                  format_func=C.STATUS_LABELS.get, key="inb_status")
        ex_id = f2.selectbox("Exercício", [None] + [e.id for e in exs], key="inb_ex",
                             format_func=lambda i: "Todos" if i is None else next(e.label for e in exs if e.id == i))
        unit = f3.selectbox("Unidade", [None] + sorted({e.unit for e in exs}), key="inb_unit",
                            format_func=lambda u: "Todas" if u is None else u)
        g1, g2, g3 = st.columns(3)
        student = g1.text_input("Estudante", key="inb_student", placeholder="Nome ou matrícula")
        rev_id = g2.selectbox("Responsável", [None] + [a.id for a in admins], key="inb_rev",
                              format_func=lambda i: "Qualquer" if i is None else next(a.full_name for a in admins if a.id == i))
        with g3:
            d0, d1 = _date_range("inb_dates")
    rows = p.reviews.inbox(user, statuses=statuses or None, exercise_id=ex_id, student_q=student, unit=unit,
                           reviewer_id=rev_id, date_from=d0, date_to=d1)
    if not rows:
        md('<div class="ex-empty ex-empty--small"><h3>Nenhuma entrega com estes filtros</h3>'
           '<p>Quando um aluno enviar uma resolução, ela aparecerá aqui.</p></div>')
        return
    for r in rows:
        with st.container(key=f"ex-row-{r['id']}"):
            c1, c2 = st.columns([5, 1.2], vertical_alignment="center")
            who = f" · em análise por {esc(r['reviewer_name'])}" if r["reviewer_name"] else ""
            c1.markdown(
                f'<div class="ex-row__top"><strong>Exercício {esc(r["code"])}</strong> — {esc(r["title"])}</div>'
                f'<div class="ex-prop__meta">{status_badge(r["status"])}<span>{esc(r["author_name"])}'
                f'{" (" + esc(r["author_matricula"]) + ")" if r["author_matricula"] else ""}</span>'
                f'<span>v{r["current_version_no"]}</span><span>enviada {esc(p.fmt(r["last_submitted_at"]))}</span>'
                f'<span>{esc(r["unit"])}{who}</span></div>',
                unsafe_allow_html=True,
            )
            c2.button("Avaliar" if r["status"] in C.PENDING_STATUSES + (C.EM_ANALISE,) else "Abrir",
                      key=f"inb-open-{r['id']}", use_container_width=True,
                      type="primary" if r["status"] in C.PENDING_STATUSES else "secondary",
                      on_click=nav_to, args=("admin",), kwargs={"a": "avaliar", "id": r["id"]})


# --------------------------------------------------------------------------- #
# Avaliação
# --------------------------------------------------------------------------- #
def _whatsapp_message(p: Platform, det: dict, rev: dict) -> str:
    ex, author = det["exercise"], det["author"]
    result = C.LEVEL_LABELS[rev["level"]] if rev["decision"] == C.DECISION_APROVADA else C.DEVOLVIDO_LABEL
    url = (p.admin.get_setting("app_url") or "").strip()
    lines = [
        f"Olá, {author.full_name.split()[0]}!",
        f"Sua resolução do Exercício {ex.code} — {ex.title} (versão v{rev['version_no']}) foi avaliada em "
        f"{p.admin.get_setting('course')}: *{result}*.",
        "Segue o parecer em PDF em anexo. Ele também está disponível na plataforma, em Alterar Resolução.",
    ]
    if rev["decision"] == C.DECISION_DEVOLVIDA:
        lines.append("Corrija os pontos indicados e envie uma nova versão pela plataforma.")
    if url:
        lines.append(url)
    return "\n\n".join(lines)


def share_panel(p: Platform, user: User, det: dict, rev: dict, key: str) -> None:
    with st.container(key=f"ex-share-{key}"):
        md('<div class="ex-panel__label">Parecer e comunicação</div>')
        c1, c2 = st.columns(2)
        with c1:
            lazy_download("Baixar parecer (PDF)", f"{key}-par-{rev['id']}", lambda: p.reviews.parecer_pdf(user, rev["id"]),
                          primary=True)
        with c2:
            st.link_button("Compartilhar pelo WhatsApp", whatsapp_link(_whatsapp_message(p, det, rev), det["author"].phone),
                           icon=":material/chat:", use_container_width=True)
        st.caption(
            "O WhatsApp não permite anexar arquivos automaticamente por link. Baixe o parecer, toque em "
            "“Compartilhar pelo WhatsApp” (a mensagem já vem preenchida"
            + (" para o número do aluno" if det["author"].phone else "; escolha o contato")
            + ") e anexe o PDF antes de enviar."
        )


def evaluate(p: Platform, user: User, sid: str | None) -> None:
    st.button("← Bandeja de revisão", key="back-inbox", on_click=nav_to, args=("admin",), kwargs={"a": "bandeja"})
    if not sid:
        st.warning("Selecione uma entrega na bandeja.")
        return
    det = p.submissions.detail(user, sid)
    sub, ex, author = det["submission"], det["exercise"], det["author"]
    versions = det["versions"]
    sent = [v for v in versions if v["state"] != C.V_RASCUNHO]
    ver = sent[-1] if sent else versions[-1]
    status = sub["status"]
    mine = status == C.EM_ANALISE and sub["reviewer_id"] == user.id

    md(
        f'<div class="ex-head"><div><div class="ex-head__kicker">Avaliação · {esc(ex.unit)}</div>'
        f'<h2>Exercício {esc(ex.code)} — {esc(ex.title)}</h2>'
        f'<p>{status_badge(status)} <strong>{esc(author.full_name)}</strong>'
        f'{" · matrícula " + esc(author.matricula) if author.matricula else ""} · versão v{ver["version_no"]}'
        f' · enviada {esc(p.fmt(ver["submitted_at"]))}'
        f'{"" if author.active else " · <em>conta desativada</em>"}</p></div></div>'
    )

    with st.container(key="ex-claim"):
        if status in C.PENDING_STATUSES:
            st.markdown("Esta entrega aguarda avaliação. Ao iniciar a análise, os materiais ficam bloqueados para o aluno "
                        "e os demais administradores veem que você é o responsável.")
            if st.button("Iniciar análise", type="primary", key="claim"):
                _, ok = run_action(p.reviews.claim, user, sid, expected_row_version=sub["row_version"])
                if ok:
                    st.rerun()
        elif status == C.EM_ANALISE and not mine:
            st.warning(f"Em análise por {det['reviewer_name']} desde {p.fmt(sub['review_started_at'])}.")
            if st.button("Assumir análise", key="takeover"):
                _, ok = run_action(p.reviews.claim, user, sid, expected_row_version=sub["row_version"], takeover=True)
                if ok:
                    st.rerun()
        elif mine:
            c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
            c1.markdown(f"Você está avaliando esta versão desde {p.fmt(sub['review_started_at'])}.")
            if c2.button("Devolver à fila", key="release", use_container_width=True):
                _, ok = run_action(p.reviews.release, user, sid, expected_row_version=sub["row_version"])
                if ok:
                    st.rerun()
        else:
            st.markdown(f"**{C.STATUS_LABELS[status]}.** Não há versão aguardando avaliação."
                        + (" O aluno está preparando uma nova versão." if versions[-1]["state"] == C.V_RASCUNHO else ""))

    left, right = st.columns([1.45, 1], gap="medium") if mine else (st.container(), None)
    with left:
        t_enun, t_video, t_pdf, t_fal, t_aluno, t_hist = st.tabs(
            ["Enunciado", "Vídeo", "PDF", "Falstad", "Aluno", "Versões e avaliações"])
        with t_enun:
            from .exercise_view import render_exercise

            render_exercise(p, ex, key=f"adm-{sid}")
        with t_video:
            if ver["youtube_id"]:
                youtube_embed(ver["youtube_id"])
                st.link_button("Abrir no YouTube", watch_url(ver["youtube_id"]), icon=":material/open_in_new:")
                info = [f"Verificação automática: {C.VIDEO_CHECK_LABELS.get(ver['video_check'] or '', 'não realizada')}"]
                if ver["youtube_title"]:
                    info.append(f"Título: {ver['youtube_title']}" + (f" · Canal: {ver['youtube_channel']}" if ver["youtube_channel"] else ""))
                if ver["video_duration_s"]:
                    src = {"api": "YouTube", "declarada": "declarada pelo aluno", "verificada": "conferida na avaliação"}
                    info.append(f"Duração: {format_duration(ver['video_duration_s'])} ({src.get(ver['video_duration_source'], '')})")
                    if ver["video_duration_s"] > float(p.admin.get_setting("max_video_minutes")) * 60:
                        st.warning("Duração acima da recomendada para a disciplina.")
                st.caption(" · ".join(info))
            else:
                st.info("Sem vídeo informado.")
        with t_pdf:
            if ver["pdf_key"]:
                try:
                    data, fname = p.submissions.version_pdf(user, ver["id"])
                    st.download_button("Baixar PDF", data, file_name=fname, mime="application/pdf", key=f"adm-pdf-{ver['id']}")
                    pdf_preview(data, f"adm-{ver['id']}")
                except AppError as exc:
                    st.error(exc.message + " Use Configurações → Integridade para diagnosticar.")
            else:
                st.info("Sem PDF.")
        with t_fal:
            if ver["falstad_url"]:
                st.link_button("Abrir Circuito no Falstad", ver["falstad_url"], type="primary",
                               icon=":material/electrical_services:")
                st.caption("Confira se o circuito corresponde ao enunciado e aos valores usados no PDF e no vídeo.")
                st.code(ver["falstad_url"][:400] + ("…" if len(ver["falstad_url"]) > 400 else ""), language=None)
        with t_aluno:
            st.markdown(
                f"**{author.full_name}**  \nLogin: `{author.login}`  \nMatrícula: {author.matricula or '—'}  \n"
                f"E-mail: {author.email or '—'}  \nWhatsApp: {author.phone or '—'}  \n"
                f"Coautores: {sub['coauthors'] or '—'}"
            )
            if ver["student_notes"]:
                md('<div class="ex-panel__label">Observações do aluno</div>')
                st.markdown(ver["student_notes"])
        with t_hist:
            for v in reversed(versions):
                st.markdown(f"**v{v['version_no']}** — {C.VERSION_LABELS[v['state']]} · "
                            f"{p.fmt(v['submitted_at']) if v['submitted_at'] else 'não enviada'}")
                cols = st.columns(3)
                if v["youtube_id"]:
                    cols[0].link_button("Vídeo", watch_url(v["youtube_id"]), use_container_width=True)
                if v["falstad_url"]:
                    cols[1].link_button("Falstad", v["falstad_url"], use_container_width=True)
                if v["pdf_key"] and v["id"] != ver["id"]:
                    with cols[2]:
                        lazy_download("PDF", f"adm-v-{v['id']}", lambda v=v: p.submissions.version_pdf(user, v["id"]))
                for rev in [r for r in det["reviews"] if r["version_id"] == v["id"]]:
                    review_block(p, user, rev, key_prefix=f"adm{v['version_no']}")

    if mine and right is not None:
        with right, st.container(key="ex-decision"):
            _decision_form(p, user, det, ver)

    last = next((r for r in det["reviews"] if r["kind"] == C.REVIEW_KIND_AVALIACAO), None)
    if last and not mine and status in (C.DEVOLVIDA, C.APROVADA):
        section_head("Última decisão", C.LEVEL_LABELS.get(last["level"], C.DEVOLVIDO_LABEL),
                     f"Registrada por {last['reviewer_name']} em {p.fmt(last['created_at'])}.")
        share_panel(p, user, det, last, "eval")


def _decision_form(p: Platform, user: User, det: dict, ver: dict) -> None:
    sub = det["submission"]
    md('<div class="ex-panel__label">Decisão acadêmica</div>')
    st.caption("Avalie qualitativamente. A plataforma não calcula notas: registra a decisão e, se aprovada, o nível.")
    k = f"{sub['id']}-{sub['row_version']}"
    with st.form(f"decide-{k}", border=False):
        md('<div class="ex-form-sub">Requisitos obrigatórios</div>')
        req = {key: st.checkbox(f"{name} — cumprido", key=f"req-{key}-{k}") for key, name in C.REQUIREMENTS}
        md('<div class="ex-form-sub">Critérios</div>')
        crit = {}
        for key, name in C.CRITERIA:
            rating = st.radio(name, list(C.RATINGS), format_func=C.RATINGS.get, horizontal=True, index=None,
                              key=f"crit-{key}-{k}")
            comment = st.text_input("Comentário", key=f"critc-{key}-{k}", label_visibility="collapsed",
                                    placeholder="Comentário sobre este critério (opcional)")
            crit[key] = {"rating": rating, "comment": comment}
        md('<div class="ex-form-sub">Decisão</div>')
        decision = st.radio("Resultado", [C.DECISION_APROVADA, C.DECISION_DEVOLVIDA], index=None, key=f"dec-{k}",
                            format_func={C.DECISION_APROVADA: "Aprovar Resolução", C.DECISION_DEVOLVIDA: "Devolver para Correção"}.get)
        level = st.radio("Nível de aprovação (obrigatório ao aprovar)", list(C.LEVELS), index=None, key=f"lvl-{k}",
                         format_func=C.LEVEL_LABELS.get, captions=[C.LEVEL_DESCRIPTIONS[lv] for lv in C.LEVELS])
        dur = st.text_input("Duração conferida do vídeo (mm:ss)", key=f"dur-{k}",
                            value=format_duration(ver["video_duration_s"]) if ver["video_duration_s"] else "")
        problems = st.text_area("Problemas identificados (obrigatório ao devolver)", key=f"prob-{k}", height=100)
        observations = st.text_area("Observações técnicas e didáticas", key=f"obs-{k}", height=90)
        recommendations = st.text_area("Recomendações concretas", key=f"rec-{k}", height=90)
        resubmit = st.text_area("Indicações para o reenvio (opcional)", key=f"res-{k}", height=70,
                                placeholder="Se vazio, o parecer inclui instruções padrão.")
        confirm = st.checkbox("Confirmo esta decisão. Ela será registrada com meu nome, data e hora.", key=f"conf-{k}")
        b1, b2 = st.columns(2)
        preview = b1.form_submit_button("Pré-visualizar parecer", use_container_width=True)
        register = b2.form_submit_button("Registrar decisão", type="primary", use_container_width=True)

    if preview:
        try:
            pdf = p.reviews.preview_parecer(user, sub["id"], decision=decision or C.DECISION_DEVOLVIDA, level=level,
                                            requirements=req, criteria=crit, problems=problems, observations=observations,
                                            recommendations=recommendations, resubmit_instructions=resubmit)
            st.session_state[f"prev-{k}"] = pdf
        except AppError as exc:
            st.error(exc.message)
    if st.session_state.get(f"prev-{k}"):
        st.download_button("Baixar prévia do parecer", st.session_state[f"prev-{k}"], file_name="previa_parecer.pdf",
                           mime="application/pdf", key=f"prevdl-{k}")
    if register:
        if decision is None:
            st.error("Selecione o resultado: aprovar ou devolver para correção.")
            return
        if not confirm:
            st.error("Marque a confirmação da decisão.")
            return
        with st.spinner("Registrando decisão e gerando parecer…"):
            if decision == C.DECISION_APROVADA:
                if level is None:
                    st.error("Selecione um dos três níveis de aprovação.")
                    return
                _, ok = run_action(p.reviews.approve, user, sub["id"], expected_row_version=sub["row_version"], level=level,
                                   requirements=req, criteria=crit, observations=observations,
                                   recommendations=recommendations, verified_duration=dur)
                msg = f"Resolução aprovada ({C.LEVEL_LABELS[level]}) e publicada na biblioteca."
            else:
                _, ok = run_action(p.reviews.return_for_correction, user, sub["id"], expected_row_version=sub["row_version"],
                                   requirements=req, criteria=crit, problems=problems, observations=observations,
                                   recommendations=recommendations, resubmit_instructions=resubmit)
                msg = "Resolução devolvida para correção. O parecer foi gerado e está disponível para o aluno."
        if ok:
            clear_public_cache()
            flash(msg)
            st.rerun()


# --------------------------------------------------------------------------- #
# Publicações
# --------------------------------------------------------------------------- #
def publications(p: Platform, user: User) -> None:
    section_head("Publicações", "Resoluções publicadas e retiradas",
                 "Ajuste o nível, retire ou restaure publicações. Toda alteração fica registrada.")
    rows = p.reviews.inbox(user, statuses=None)
    rows = [r for r in rows if r["published_version_id"]]
    show = st.radio("Mostrar", ["Publicadas", "Retiradas", "Todas"], horizontal=True, key="pub_show")
    if show == "Publicadas":
        rows = [r for r in rows if r["is_published"]]
    elif show == "Retiradas":
        rows = [r for r in rows if not r["is_published"]]
    if not rows:
        st.info("Nenhuma publicação nesta categoria.")
        return
    for r in rows:
        with st.container(key=f"ex-row-pub-{r['id']}"):
            st.markdown(
                f'<div class="ex-row__top"><strong>Exercício {esc(r["code"])}</strong> — {esc(r["title"])}</div>'
                f'<div class="ex-prop__meta">{status_badge(r["status"])}{level_badge(r["published_level"])}'
                f'<span>{esc(r["author_name"])}</span><span>publicada em {esc(p.fmt(r["published_at"]))}</span>'
                f'{"<span class=ex-alert>" + esc(r["resource_alert"]) + "</span>" if r["resource_alert"] else ""}</div>',
                unsafe_allow_html=True,
            )
            with st.expander("Gerenciar"):
                st.button("Abrir avaliação", key=f"pub-open-{r['id']}", on_click=nav_to, args=("admin",),
                          kwargs={"a": "avaliar", "id": r["id"]})
                if r["is_published"]:
                    st.button("Ver na biblioteca", key=f"pub-lib-{r['id']}", on_click=nav_to, args=("resolucao",),
                              kwargs={"r": r["id"]})
                    with st.form(f"lvl-{r['id']}-{r['row_version']}"):
                        lv = st.radio("Novo nível", list(C.LEVELS), format_func=C.LEVEL_LABELS.get, horizontal=True,
                                      index=list(C.LEVELS).index(r["published_level"]))
                        just = st.text_input("Justificativa *")
                        if st.form_submit_button("Alterar nível"):
                            _, ok = run_action(p.reviews.change_level, user, r["id"], expected_row_version=r["row_version"],
                                               level=lv, justification=just, success="Nível alterado.")
                            if ok:
                                clear_public_cache()
                                st.rerun()
                    with st.form(f"ret-{r['id']}-{r['row_version']}"):
                        reason = st.text_input("Motivo da retirada *", placeholder="Ex.: vídeo removido pelo autor")
                        if st.form_submit_button("Retirar publicação"):
                            _, ok = run_action(p.reviews.retire, user, r["id"], expected_row_version=r["row_version"],
                                               reason=reason, success="Publicação retirada da biblioteca.")
                            if ok:
                                clear_public_cache()
                                st.rerun()
                elif r["status"] == C.RETIRADA:
                    st.caption(f"Motivo da retirada: {r['retired_reason'] or '—'}")
                    if st.button("Restaurar publicação", key=f"pub-rest-{r['id']}"):
                        _, ok = run_action(p.reviews.restore, user, r["id"], expected_row_version=r["row_version"],
                                           success="Publicação restaurada.")
                        if ok:
                            clear_public_cache()
                            st.rerun()


# --------------------------------------------------------------------------- #
# Exercícios
# --------------------------------------------------------------------------- #
def _exercise_fields(p: Platform, prefix: str, ex=None) -> dict:
    units = list(p.admin.get_setting("units") or [])
    if ex and ex.unit and ex.unit not in units:
        units.append(ex.unit)
    c1, c2 = st.columns([1, 3])
    code = c1.text_input("Código *", value=ex.code if ex else "", placeholder="2.04", key=f"{prefix}-code",
                         help="Formato capítulo.número. Não pode ser alterado depois que houver entregas.")
    title = c2.text_input("Título *", value=ex.title if ex else "", key=f"{prefix}-title")
    unit = st.selectbox("Unidade ou tema *", units, index=units.index(ex.unit) if ex and ex.unit in units else None,
                        key=f"{prefix}-unit", accept_new_options=True, placeholder="Selecione ou digite uma nova")
    topics = st.text_input("Temas e conceitos (separados por vírgula)", value=ex.topics if ex else "",
                           key=f"{prefix}-topics", placeholder="malhas, LKT, sistemas lineares")
    statement = st.text_area("Enunciado *", value=ex.statement if ex else "", height=160, key=f"{prefix}-stmt",
                             help="Aceita Markdown e LaTeX entre cifrões, por exemplo $V = RI$.")
    desc = st.text_area("Descrição complementar", value=ex.description if ex else "", height=70, key=f"{prefix}-desc")
    mat = st.text_area("Materiais de apoio (links, referências)", value=ex.support_material if ex else "", height=70,
                       key=f"{prefix}-mat")
    return dict(code=code, title=title, unit=unit or "", topics=topics, statement=statement, description=desc,
                support_material=mat)


def exercises(p: Platform, user: User) -> None:
    exs = p.exercises.list(user, include_inactive=True)
    section_head("Gerenciar Exercícios", "Exercícios Propostos",
                 "Somente exercícios ativos aparecem para os alunos.", count=len(exs))
    with st.expander("Novo exercício", expanded=not exs):
        with st.form("ex-new", clear_on_submit=False):
            fields = _exercise_fields(p, "new")
            active = st.checkbox("Disponível para entregas", value=True)
            ok = st.form_submit_button("Criar exercício", type="primary")
        if ok:
            ex, success = run_action(p.exercises.create, user, active=active, **fields)
            if success:
                flash(f"Exercício {ex.code} criado.")
                for k in list(st.session_state):
                    if k.startswith("new-"):
                        del st.session_state[k]
                st.rerun()
    from ..services.exercises import list_label

    f1, f2 = st.columns([3, 2])
    q = f1.text_input("Filtrar", key="admex_q", placeholder="Código ou título")
    sel_l = f2.multiselect("Lista", sorted({list_label(e.code) for e in exs}), key="admex_l", placeholder="Todas")
    for ex in exs:
        if q and q.lower() not in f"{ex.code} {ex.title}".lower():
            continue
        if sel_l and list_label(ex.code) not in sel_l:
            continue
        with st.container(key=f"ex-row-ex-{ex.id}"):
            st.markdown(
                f'<div class="ex-row__top"><strong>Exercício {esc(ex.code)}</strong> — {esc(ex.title)}</div>'
                f'<div class="ex-prop__meta"><span class="ex-badge ex-badge--{"ok" if ex.active else "muted"}">'
                f'{"Ativo" if ex.active else "Inativo"}</span><span>{esc(ex.unit)}</span>'
                f'<span>{ex.submissions_count} entrega(s)</span></div>',
                unsafe_allow_html=True,
            )
            with st.expander("Editar"):
                with st.form(f"ex-edit-{ex.id}"):
                    fields = _exercise_fields(p, f"ed-{ex.id}", ex)
                    if st.form_submit_button("Salvar alterações", type="primary"):
                        _, success = run_action(p.exercises.update, user, ex.id, success="Exercício atualizado.", **fields)
                        if success:
                            st.rerun()
                _figures_admin(p, user, ex)
                c1, c2 = st.columns(2)
                if c1.button("Desativar" if ex.active else "Ativar", key=f"ex-tg-{ex.id}"):
                    _, success = run_action(p.exercises.set_active, user, ex.id, not ex.active, success="Disponibilidade alterada.")
                    if success:
                        st.rerun()
                if ex.submissions_count == 0:
                    if c2.checkbox("Confirmar exclusão", key=f"ex-delok-{ex.id}") and c2.button("Excluir", key=f"ex-del-{ex.id}"):
                        _, success = run_action(p.exercises.delete, user, ex.id, success="Exercício excluído.")
                        if success:
                            st.rerun()
                else:
                    c2.caption("Exercícios com entregas não podem ser excluídos; desative-os.")


def _figures_admin(p: Platform, user: User, ex) -> None:
    from .exercise_view import clear_figure_cache

    md('<div class="ex-form-sub">Figuras do enunciado</div>')
    figs = p.exercises.figures(ex.id)
    if not figs:
        st.caption("Nenhuma figura. Se o enunciado cita um circuito, anexe a imagem abaixo.")
    for fig in figs:
        c1, c2, c3 = st.columns([1.6, 2.6, 1.2], vertical_alignment="center")
        try:
            c1.image(p.exercises.figure_bytes(fig), use_container_width=True)
        except AppError as exc:
            c1.warning(exc.message)
        origem = "pacote do repositório" if fig.source == "pacote" else "enviada pela administração"
        c2.markdown(f"**{fig.label or 'Figura'}**  \n{fig.caption}  \n<small>{origem}</small>", unsafe_allow_html=True)
        if c3.button("Remover", key=f"fig-rm-{fig.id}"):
            _, ok = run_action(p.exercises.remove_figure, user, fig.id, success="Figura removida.")
            if ok:
                clear_figure_cache()
                st.rerun()
    with st.form(f"fig-add-{ex.id}", clear_on_submit=True):
        up = st.file_uploader("Adicionar figura (PNG ou JPEG, até 5 MB)", type=["png", "jpg", "jpeg"])
        c1, c2 = st.columns(2)
        label = c1.text_input("Rótulo", placeholder="Figura 8.114")
        caption = c2.text_input("Legenda / referência", placeholder="Boylestad, 12ª ed., p. 279")
        if st.form_submit_button("Anexar figura"):
            if up is None:
                st.error("Selecione uma imagem.")
            else:
                _, ok = run_action(p.exercises.add_figure, user, ex.id, up.getvalue(), label=label, caption=caption,
                                   success="Figura anexada ao exercício.")
                if ok:
                    clear_figure_cache()
                    st.rerun()


# --------------------------------------------------------------------------- #
# Usuários
# --------------------------------------------------------------------------- #
def _credentials_box() -> None:
    creds = st.session_state.get("_new_creds")
    if not creds:
        return
    with st.container(key="ex-creds"):
        md('<div class="ex-panel__label">Credenciais geradas — exibidas apenas agora</div>')
        st.dataframe(pd.DataFrame(creds), hide_index=True, use_container_width=True)
        st.download_button("Baixar credenciais (CSV)", to_csv(creds, [("nome", "Nome"), ("login", "Login"),
                                                                       ("senha_provisoria", "Senha provisória"),
                                                                       ("resultado", "Resultado")]),
                           file_name="credenciais_provisorias.csv", mime="text/csv")
        st.caption("Entregue cada senha de forma privada. No primeiro acesso, o sistema exige a troca da senha.")
        if st.button("Já entreguei; ocultar credenciais"):
            st.session_state.pop("_new_creds", None)
            st.rerun()


def add_users(p: Platform, user: User) -> None:
    section_head("Adicionar Usuários", "Cadastrar alunos e administradores",
                 "Senhas provisórias são geradas automaticamente e precisam ser trocadas no primeiro acesso.")
    _credentials_box()
    c1, c2 = st.columns(2, gap="large")
    with c1, st.container(key="ex-panel-adduser"):
        md('<div class="ex-panel__label">Cadastro individual</div>')
        with st.form("add-user", clear_on_submit=True):
            name = st.text_input("Nome completo *")
            login_v = st.text_input("Login *", help="Sugestão: matrícula (alunos) ou e-mail institucional.")
            mat = st.text_input("Matrícula")
            email = st.text_input("E-mail")
            phone = st.text_input("WhatsApp", placeholder="+5545999998888")
            role = st.radio("Perfil", list(C.ROLES), format_func=C.ROLES.get, horizontal=True)
            st.caption("Administradores têm acesso completo: avaliar, publicar, gerenciar usuários e configurações.")
            ok = st.form_submit_button("Cadastrar", type="primary")
        if ok:
            res, success = run_action(p.users.create, user, login=login_v, full_name=name, email=email, matricula=mat,
                                      phone=phone, role=role)
            if success:
                u, temp = res
                st.session_state["_new_creds"] = [{"nome": u.full_name, "login": u.login, "senha_provisoria": temp,
                                                   "resultado": f"{C.ROLES[u.role]} criado"}]
                st.rerun()
    with c2, st.container(key="ex-panel-csv"):
        md('<div class="ex-panel__label">Importar turma (CSV)</div>')
        st.caption("Colunas: nome; matricula; email; telefone (opcional); login (opcional — padrão: matrícula).")
        st.download_button("Baixar modelo CSV", "nome;matricula;email;telefone\nMaria Exemplo;2026001;maria@aluno.unila.edu.br;\n".encode("utf-8-sig"),
                           file_name="modelo_alunos.csv", mime="text/csv")
        up = st.file_uploader("Arquivo CSV", type=["csv"], key="csv-up")
        if up is not None and st.button("Importar alunos", type="primary"):
            text = up.getvalue().decode("utf-8-sig", errors="replace")
            report, success = run_action(p.users.import_students_csv, user, text)
            if success:
                st.session_state["_new_creds"] = report
                created = sum(1 for r in report if r["resultado"] == "Criado")
                flash(f"{created} aluno(s) criado(s); {len(report) - created} linha(s) com problema.",
                      "success" if created else "warning")
                st.rerun()


def manage_users(p: Platform, user: User) -> None:
    section_head("Gerenciar Usuários", "Contas da plataforma",
                 "Desativar uma conta bloqueia o acesso, mas preserva entregas, avaliações e publicações.")
    _credentials_box()
    f1, f2, f3 = st.columns([3, 1.5, 1.5])
    q = f1.text_input("Buscar", key="usr_q", placeholder="Nome, login, e-mail ou matrícula")
    role = f2.selectbox("Perfil", [None, C.ROLE_ALUNO, C.ROLE_ADMIN], key="usr_role",
                        format_func=lambda r: "Todos" if r is None else C.ROLES[r])
    act = f3.selectbox("Situação", [None, True, False], key="usr_act",
                       format_func=lambda a: "Todas" if a is None else ("Ativas" if a else "Desativadas"))
    users = p.users.list(user, q=q, role=role, active=act)
    st.caption(f"{len(users)} conta(s)")
    for u in users[:200]:
        with st.container(key=f"ex-row-usr-{u.id}"):
            st.markdown(
                f'<div class="ex-row__top"><strong>{esc(u.full_name)}</strong> · <code>{esc(u.login)}</code></div>'
                f'<div class="ex-prop__meta"><span class="ex-badge ex-badge--{"info" if u.role == C.ROLE_ADMIN else "neutral"}">'
                f'{C.ROLES[u.role]}</span><span class="ex-badge ex-badge--{"ok" if u.active else "muted"}">'
                f'{"Ativa" if u.active else "Desativada"}</span>'
                f'<span>{esc(u.matricula or "")}</span><span>{esc(u.email or "")}</span>'
                f'<span>último acesso: {esc(p.fmt(u.last_login_at))}</span></div>',
                unsafe_allow_html=True,
            )
            with st.expander("Gerenciar"):
                with st.form(f"usr-edit-{u.id}"):
                    c1, c2 = st.columns(2)
                    name = c1.text_input("Nome completo", value=u.full_name)
                    pub = c2.text_input("Nome exibido publicamente", value=u.public_name or "")
                    login_v = c1.text_input("Login", value=u.login)
                    mat = c2.text_input("Matrícula", value=u.matricula or "")
                    email = c1.text_input("E-mail", value=u.email or "")
                    phone = c2.text_input("WhatsApp", value=u.phone or "")
                    if st.form_submit_button("Salvar dados"):
                        _, ok = run_action(p.users.update_profile, user, u.id, full_name=name, public_name=pub, login=login_v,
                                           matricula=mat, email=email, phone=phone, success="Dados atualizados.")
                        if ok:
                            st.rerun()
                c1, c2, c3 = st.columns(3)
                new_role = C.ROLE_ALUNO if u.role == C.ROLE_ADMIN else C.ROLE_ADMIN
                label = "Revogar administração" if u.role == C.ROLE_ADMIN else "Tornar administrador"
                if c1.button(label, key=f"usr-role-{u.id}", use_container_width=True):
                    _, ok = run_action(p.users.set_role, user, u.id, new_role, success="Perfil alterado.")
                    if ok:
                        st.rerun()
                if c2.button("Desativar conta" if u.active else "Reativar conta", key=f"usr-act-{u.id}", use_container_width=True):
                    _, ok = run_action(p.users.set_active, user, u.id, not u.active, success="Situação da conta alterada.")
                    if ok:
                        st.rerun()
                if c3.button("Gerar senha provisória", key=f"usr-pwd-{u.id}", use_container_width=True):
                    temp, ok = run_action(p.users.reset_password, user, u.id)
                    if ok:
                        st.session_state["_new_creds"] = [{"nome": u.full_name, "login": u.login, "senha_provisoria": temp,
                                                           "resultado": "Senha redefinida"}]
                        st.rerun()
                if st.toggle("Ver atividade", key=f"usr-log-{u.id}"):
                    rows = p.admin.logs(user, user_id=u.id, limit=100)
                    _log_table(p, rows)


# --------------------------------------------------------------------------- #
# Logs e histórico
# --------------------------------------------------------------------------- #
LOG_COLUMNS = [("quando", "Data e hora"), ("category", "Categoria"), ("action", "Evento"), ("actor_login", "Usuário"),
               ("summary", "Descrição"), ("target_type", "Alvo"), ("target_id", "ID do alvo"), ("details_json", "Detalhes")]


def _log_table(p: Platform, rows: list[dict]) -> list[dict]:
    for r in rows:
        r["quando"] = p.fmt(r["ts"])
        r["category"] = C.LOG_CATEGORIES.get(r["category"], r["category"])
    if not rows:
        st.caption("Nenhum registro.")
        return rows
    df = pd.DataFrame(rows)[["quando", "category", "action", "actor_login", "summary"]]
    df.columns = ["Data e hora", "Categoria", "Evento", "Usuário", "Descrição"]
    st.dataframe(df, hide_index=True, use_container_width=True, height=min(600, 38 + 35 * len(df)))
    return rows


def logs(p: Platform, user: User, categories: list[str], title: str) -> None:
    section_head("Auditoria", title, "Registros não incluem senhas, tokens nem segredos.")
    f1, f2, f3 = st.columns([3, 2, 1.2])
    q = f1.text_input("Buscar", key=f"log_q_{title}", placeholder="Evento, usuário ou descrição")
    with f2:
        d0, d1 = _date_range(f"log_d_{title}")
    limit = f3.selectbox("Máximo", [200, 1000, 5000], key=f"log_l_{title}")
    rows = p.admin.logs(user, categories=categories, q=q, date_from=d0, date_to=d1, limit=limit)
    rows = _log_table(p, rows)
    if rows:
        st.download_button("Exportar CSV", to_csv(rows, LOG_COLUMNS), file_name=f"{title.lower().replace(' ', '_')}.csv",
                           mime="text/csv", icon=":material/download:")


def history(p: Platform, user: User) -> None:
    section_head("Auditoria", "Histórico de Avaliações", "Cada decisão com avaliador, data, versão, resultado e parecer.")
    admins = p.users.list(user, role=C.ROLE_ADMIN) + p.users.list(user, role=C.ROLE_ALUNO)
    f1, f2, f3 = st.columns([2.5, 1.5, 2])
    q = f1.text_input("Buscar", key="hist_q", placeholder="Aluno, código ou título")
    dec = f2.selectbox("Resultado", [None, C.DECISION_APROVADA, C.DECISION_DEVOLVIDA], key="hist_dec",
                       format_func=lambda d: "Todos" if d is None else C.DECISION_LABELS[d])
    rev = f3.selectbox("Avaliador", [None] + [a.id for a in admins if a.role == C.ROLE_ADMIN], key="hist_rev",
                       format_func=lambda i: "Todos" if i is None else next(a.full_name for a in admins if a.id == i))
    rows = p.reviews.history(user, decision=dec, reviewer_id=rev, q=q)
    if not rows:
        st.info("Nenhuma avaliação registrada com estes filtros.")
        return
    for r in rows:
        r["quando"] = p.fmt(r["created_at"])
        r["resultado"] = (f"Ajuste de nível → {C.LEVEL_SHORT[r['level']]}" if r["kind"] == C.REVIEW_KIND_AJUSTE else
                          C.LEVEL_LABELS[r["level"]] if r["level"] else C.DEVOLVIDO_LABEL)
        r["exercicio"] = f"{r['code']} — {r['title']}"
        r["versao"] = f"v{r['version_no']}"
        r["parecer"] = "sim" if r["parecer_key"] else "—"
    cols = [("quando", "Data e hora"), ("exercicio", "Exercício"), ("author_name", "Aluno"), ("versao", "Versão"),
            ("resultado", "Resultado"), ("reviewer_name", "Avaliador"), ("parecer", "Parecer")]
    df = pd.DataFrame(rows)[[c for c, _ in cols]]
    df.columns = [label for _, label in cols]
    st.dataframe(df, hide_index=True, use_container_width=True)
    export_cols = cols + [("problems", "Problemas"), ("observations", "Observações"), ("recommendations", "Recomendações")]
    st.download_button("Exportar CSV", to_csv(rows, export_cols), file_name="historico_avaliacoes.csv", mime="text/csv",
                       icon=":material/download:")
    with_pdf = [r for r in rows if r["parecer_key"]]
    if with_pdf:
        md('<div class="ex-panel__label">Consultar um parecer</div>')
        rid = st.selectbox("Avaliação", [r["id"] for r in with_pdf], key="hist_pick",
                           format_func=lambda i: next(f"{r['quando']} · {r['exercicio']} · {r['author_name']} · {r['resultado']}"
                                                      for r in with_pdf if r["id"] == i))
        sel = next(r for r in with_pdf if r["id"] == rid)
        det = p.submissions.detail(user, sel["submission_id"])
        rev_full = next(x for x in det["reviews"] if x["id"] == rid)
        share_panel(p, user, det, rev_full, f"hist-{rid}")


# --------------------------------------------------------------------------- #
# Configurações, integridade e backup
# --------------------------------------------------------------------------- #
def config(p: Platform, user: User) -> None:
    section_head("Configurações", "Parâmetros acadêmicos e operacionais")
    s = p.admin.all_settings(user)
    with st.form("settings"):
        c1, c2 = st.columns(2)
        inst = c1.text_input("Instituição", value=s.get("institution", ""))
        course = c2.text_input("Disciplina", value=s.get("course", ""))
        sem = c1.text_input("Semestre", value=s.get("semester", ""), placeholder="2026.2")
        prof = c2.text_input("Professor(a) responsável", value=s.get("professor", ""))
        url = st.text_input("Endereço público da plataforma", value=s.get("app_url", ""),
                            placeholder="https://circuitos-eletricos.streamlit.app", help="Incluído nas mensagens de WhatsApp.")
        c3, c4 = st.columns(2)
        max_pdf = c3.number_input("Tamanho máximo do PDF (MB)", 1.0, float(C.HARD_MAX_PDF_MB), float(s.get("max_pdf_mb", 10)), 1.0)
        max_vid = c4.number_input("Duração recomendada do vídeo (min)", 1.0, 60.0, float(s.get("max_video_minutes", 8)), 1.0)
        code = st.text_input("Código da turma para autocadastro", value=s.get("self_registration_code", ""),
                             help="Deixe vazio para desativar o autocadastro. Alunos cadastrados por código entram sempre como Aluno.")
        units = st.text_area("Unidades e temas (um por linha)", value="\n".join(s.get("units", [])), height=140)
        ok = st.form_submit_button("Salvar configurações", type="primary")
    if ok:
        _, success = run_action(p.admin.update_settings, user, {
            "institution": inst, "course": course, "semester": sem, "professor": prof, "app_url": url,
            "max_pdf_mb": max_pdf, "max_video_minutes": max_vid, "self_registration_code": code,
            "units": units.splitlines()}, success="Configurações salvas.")
        if success:
            st.rerun()

    section_head("Conteúdo", "Pacotes de exercícios",
                 "Exercícios e figuras versionados no repositório e cadastrados automaticamente na inicialização.")
    from .. import importacao

    for spec in importacao.PACKS:
        status = importacao.pack_status(p, spec["id"])
        with st.container(key=f"ex-panel-pack-{spec['id']}"):
            st.markdown(f"**{spec['nome']}**")
            if status:
                st.markdown(
                    f"Importado em {status['aplicado_em_utc'].replace('T', ' ')} UTC · versão `{status['versao']}` · "
                    f"{status['fichas']} fichas · {len(status['criados'])} criado(s) na última aplicação"
                    + (f" · códigos mantidos sem alteração: {', '.join(status['mantidos_sem_alteracao'])}"
                       if status["mantidos_sem_alteracao"] else "")
                )
            else:
                st.markdown("Ainda não importado.")
            st.caption("“Importar ausentes” recria somente os códigos que não existem no banco (por exemplo, "
                       "um exercício excluído). Exercícios já cadastrados nunca são sobrescritos.")
            if st.button("Importar ausentes", key=f"pack-{spec['id']}"):
                rep, ok = run_action(importacao.reimport, p, user, spec["id"])
                if ok:
                    from .exercise_view import clear_figure_cache

                    clear_figure_cache()
                    flash(f"{len(rep['criados'])} exercício(s) criado(s); {len(rep['mantidos_sem_alteracao'])} já existiam.")
                    st.rerun()

    section_head("Diagnóstico", "Serviços conectados")
    for name, detail, healthy in p.admin.diagnostics(user):
        st.markdown(f"{'🟢' if healthy else '🟠'} **{name}:** {detail}")

    section_head("Integridade", "Verificar recursos das publicações",
                 "Confere se os PDFs e pareceres existem no armazenamento, se os links do Falstad são válidos "
                 "e, opcionalmente, se os vídeos continuam disponíveis no YouTube.")
    videos = st.checkbox("Verificar também os vídeos no YouTube (mais lento)", value=True, key="int_videos")
    if st.button("Executar verificação", key="int_run"):
        with st.spinner("Verificando…"):
            issues, ok = run_action(p.admin.integrity_check, user, check_videos=videos)
        if ok:
            st.session_state["_integrity"] = issues
            clear_public_cache()
    issues = st.session_state.get("_integrity")
    if issues is not None:
        if not issues:
            st.success("Nenhum problema encontrado.")
        else:
            st.dataframe(pd.DataFrame(issues)[["tipo", "onde", "detalhe"]].rename(
                columns={"tipo": "Tipo", "onde": "Onde", "detalhe": "Detalhe"}), hide_index=True, use_container_width=True)
            st.caption("Publicações com problemas exibem um aviso aos visitantes. Para corrigir: retire a publicação, "
                       "peça ao aluno uma nova versão ou regenere o parecer abaixo.")
            for i in issues:
                if i["review_id"] and st.button(f"Regenerar parecer — {i['onde']}", key=f"regen-{i['review_id']}"):
                    _, ok = run_action(p.reviews.regenerate_parecer, user, i["review_id"], success="Parecer regenerado.")
                    if ok:
                        st.session_state.pop("_integrity", None)
                        st.rerun()

    section_head("Backup", "Exportar todos os dados",
                 "Arquivo ZIP com usuários, exercícios, entregas, versões, avaliações, logs, PDFs e pareceres. "
                 "Use-o para guardar uma cópia de segurança ou migrar de provedor (scripts/restaurar_backup.py).")
    hashes = st.checkbox("Incluir hashes de senha (permite restaurar as contas sem redefinir senhas)", value=True)
    st.caption("O backup contém dados pessoais e entregas não publicadas: guarde-o em local privado (nunca no GitHub).")
    if st.button("Gerar backup", key="bk-run"):
        with st.spinner("Gerando backup…"):
            blob, ok = run_action(p.admin.export_backup, user, include_password_hashes=hashes)
        if ok:
            st.session_state["_backup"] = blob
    if st.session_state.get("_backup"):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        st.download_button("Baixar backup (ZIP)", st.session_state["_backup"], file_name=f"backup_ce1_{stamp}.zip",
                           mime="application/zip", type="primary")

    section_head("Continuidade", "Transferência da administração")
    st.markdown(
        "1. Cadastre a pessoa que assumirá (Adicionar Usuários → perfil **Administrador**).  \n"
        "2. Ela entra, troca a senha provisória e confirma o acesso.  \n"
        "3. Transfira também o acesso ao **Supabase**, ao **Streamlit Cloud** e ao **GitHub** (veja `docs/GUIA_ADMINISTRATIVO.md`).  \n"
        "4. Só então revogue a administração da pessoa que está saindo. O sistema impede remover o último administrador."
    )


__all__ = ["SECTIONS", "shell", "json"]
