"""Área do aluno: Exercícios Propostos, Submeter Resolução e Alterar Resolução."""

from __future__ import annotations

import hashlib

import streamlit as st

from .. import constants as C
from ..errors import AppError
from ..services import Platform, User
from ..validators import format_duration, parse_youtube_id, watch_url
from .runtime import flash, go, nav_to, run_action
from ..services.exercises import list_label
from .exercise_view import render_exercise
from .views_public import clear_public_cache, published_items
from .widgets import chips, empty_state, esc, level_badge, md, pdf_preview, section_head, status_badge, youtube_embed


# --------------------------------------------------------------------------- #
# Utilitário: download de arquivo privado sob demanda
# --------------------------------------------------------------------------- #
def lazy_download(label: str, key: str, fetch, *, primary: bool = False) -> None:
    """Busca o arquivo só quando solicitado (evita tráfego e mantém a permissão no servidor)."""
    store = st.session_state.setdefault("_dl", {})
    if key in store:
        data, name = store[key]
        st.download_button(label, data, file_name=name, mime="application/pdf", key=f"dlb-{key}",
                           type="primary" if primary else "secondary", icon=":material/download:")
        return
    if st.button(label, key=f"prep-{key}", type="primary" if primary else "secondary", icon=":material/download:"):
        try:
            store[key] = fetch()
            if len(store) > 12:
                store.pop(next(iter(store)))
            st.rerun()
        except AppError as exc:
            st.error(exc.message)


def materials_checklist(ver: dict) -> None:
    rows = [
        ("Vídeo no YouTube", bool(ver.get("youtube_id")), "link informado" if ver.get("youtube_id") else "pendente"),
        ("PDF da resolução", bool(ver.get("pdf_key")),
         f"{esc(ver['pdf_filename'] or '')} · {ver['pdf_pages']} pág." if ver.get("pdf_key") else "pendente"),
        ("Circuito no Falstad", bool(ver.get("falstad_url")), "link informado" if ver.get("falstad_url") else "pendente"),
    ]
    items = "".join(
        f'<li class="{"ok" if ok else "todo"}"><span class="ex-check__mark" aria-hidden="true">{"✓" if ok else "○"}</span>'
        f'<span class="ex-check__name">{name}</span><span class="ex-check__state">{state}</span></li>'
        for name, ok, state in rows
    )
    md(f'<ul class="ex-check" aria-label="Situação dos materiais salvos">{items}</ul>')


def review_block(p: Platform, user: User, rev: dict, *, key_prefix: str) -> None:
    approved = rev["decision"] == C.DECISION_APROVADA
    if rev["kind"] == C.REVIEW_KIND_AJUSTE:
        md(f'<div class="ex-review ex-review--adj"><strong>Ajuste de nível</strong> por {esc(rev["reviewer_name"])} '
           f'em {esc(p.fmt(rev["created_at"]))}: {esc(C.LEVEL_SHORT.get(rev["previous_level"], "—"))} → '
           f'{esc(C.LEVEL_SHORT[rev["level"]])}<br><span>{esc(rev["observations"])}</span></div>')
        return
    title = C.LEVEL_LABELS[rev["level"]] if approved else C.DEVOLVIDO_LABEL
    parts = []
    for label, field in (("Problemas identificados", "problems"), ("Observações", "observations"),
                         ("Recomendações", "recommendations"), ("Indicações para o reenvio", "resubmit_instructions")):
        if rev.get(field):
            parts.append(f"<dt>{label}</dt><dd>{esc(rev[field])}</dd>")
    md(
        f'<div class="ex-review ex-review--{"ok" if approved else "warn"}">'
        f'<div class="ex-review__top"><strong>{esc(title)}</strong>'
        f'<span>v{rev["version_no"]} · {esc(rev["reviewer_name"])} · {esc(p.fmt(rev["created_at"]))}</span></div>'
        f'<dl>{"".join(parts)}</dl></div>'
    )
    if rev.get("parecer_key"):
        lazy_download("Baixar parecer (PDF)", f"{key_prefix}-par-{rev['id']}",
                      lambda: p.reviews.parecer_pdf(user, rev["id"]))


# --------------------------------------------------------------------------- #
# Exercícios Propostos
# --------------------------------------------------------------------------- #
def proposed(p: Platform, user: User) -> None:
    exs = p.exercises.list(user)
    mine = {s["exercise_id"]: s for s in p.submissions.mine(user)} if user.is_student else {}
    n_pub: dict[str, int] = {}
    for it in published_items():
        n_pub[it["exercise_id"]] = n_pub.get(it["exercise_id"], 0) + 1

    section_head("Exercícios Propostos", "Escolha um exercício para resolver",
                 "Publicados pela equipe da disciplina. Cada entrega exige vídeo no YouTube, PDF e circuito no Falstad.",
                 count=len(exs))
    if not exs:
        empty_state("Nenhum exercício disponível no momento", "A administração ainda não publicou exercícios propostos.", "✎")
        return
    f1, f2, f3 = st.columns([3, 1.6, 2.4])
    q = f1.text_input("Buscar exercício", key="prop_q", placeholder="Número, título, tema ou figura (ex.: 8.114)")
    listas = sorted({list_label(e.code) for e in exs})
    sel_listas = f2.multiselect("Lista", listas, key="prop_listas", placeholder="Todas")
    units = sorted({e.unit for e in exs})
    sel = f3.multiselect("Unidade ou tema", units, key="prop_units", placeholder="Todas")
    from ..services.catalog import fold

    shown = 0
    for ex in exs:
        if sel_listas and list_label(ex.code) not in sel_listas:
            continue
        if sel and ex.unit not in sel:
            continue
        hay = fold(f"{ex.code} {ex.title} {ex.topics} {ex.unit} {ex.statement} {ex.support_material}")
        if q and not all(t in hay for t in fold(q).split()):
            continue
        shown += 1
        sub = mine.get(ex.id)
        with st.container(key=f"ex-prop-{ex.id}"):
            c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
            with c1:
                pub = n_pub.get(ex.id, 0)
                md(
                    f'<div class="ex-prop__code">{esc(list_label(ex.code))} · Exercício {esc(ex.code)}</div>'
                    f'<div class="ex-prop__title">{esc(ex.title)}</div>'
                    f'<div class="ex-prop__meta"><span>{esc(ex.unit)}</span>'
                    f'{f"<span>{pub} resolução(ões) publicada(s)</span>" if pub else ""}'
                    f'{status_badge(sub["status"]) if sub else ""}</div>'
                    f'<div class="ex-prop__chips">{chips(ex.topic_list)}</div>'
                )
            with c2:
                if user.is_student:
                    if sub is None:
                        st.button("Resolver este exercício", key=f"start-{ex.id}", type="primary", use_container_width=True,
                                  on_click=nav_to, args=("submeter",), kwargs={"ex": ex.id})
                    else:
                        st.button("Abrir minha entrega", key=f"mine-{ex.id}", use_container_width=True,
                                  on_click=nav_to, args=("submissao",), kwargs={"id": sub["id"]})
            with st.expander("Ver enunciado e circuito"):
                render_exercise(p, ex, key=f"prop-{ex.id}")
    if shown == 0:
        empty_state("Nenhum exercício com estes filtros", "Remova algum filtro ou tente outro termo de busca.", "⌕")


# --------------------------------------------------------------------------- #
# Submeter Resolução
# --------------------------------------------------------------------------- #
def _choose_exercise(p: Platform, user: User, preselect: str | None) -> None:
    section_head("Submeter Resolução", "Escolha o exercício",
                 "Somente exercícios publicados pela administração podem receber entregas.")
    exs = p.exercises.list(user)
    if not exs:
        empty_state("Nenhum exercício disponível", "Aguarde a publicação de exercícios propostos.", "✎")
        return
    ids = [e.id for e in exs]
    idx = ids.index(preselect) if preselect in ids else 0
    with st.container(key="ex-panel-choose"):
        ex_id = st.selectbox("Exercício *", ids, index=idx, format_func=lambda i: next(e.label for e in exs if e.id == i))
        ex = next(e for e in exs if e.id == ex_id)
        md(f'<div class="ex-prop__meta"><span>{esc(list_label(ex.code))}</span><span>{esc(ex.unit)}</span></div>'
           f'<div class="ex-prop__chips">{chips(ex.topic_list)}</div>')
        render_exercise(p, ex, key=f"choose-{ex.id}")
        existing = next((s for s in p.submissions.mine(user) if s["exercise_id"] == ex_id), None)
        if existing:
            st.info("Você já possui uma entrega para este exercício. Correções e melhorias são feitas como novas versões dela.")
            st.button("Abrir minha entrega", type="primary", on_click=nav_to, args=("submissao",), kwargs={"id": existing["id"]})
        elif st.button("Iniciar entrega", type="primary"):
            sid, ok = run_action(p.submissions.start, user, ex_id)
            if ok:
                go("submeter", id=sid)


def submit(p: Platform, user: User, sid: str | None, ex_pre: str | None) -> None:
    if not sid:
        _choose_exercise(p, user, ex_pre)
        return
    det = p.submissions.detail(user, sid)
    sub, ver, ex = det["submission"], det["current"], det["exercise"]
    if ver["state"] != C.V_RASCUNHO:
        st.info("Esta entrega não está em edição. Acompanhe o estado ou prepare uma nova versão em Alterar Resolução.")
        st.button("Abrir entrega", type="primary", on_click=nav_to, args=("submissao",), kwargs={"id": sid})
        return

    max_mb = float(p.admin.get_setting("max_pdf_mb"))
    max_min = float(p.admin.get_setting("max_video_minutes"))
    md(
        f'<div class="ex-head"><div><div class="ex-head__kicker">Submeter Resolução · versão v{ver["version_no"]}</div>'
        f'<h2>Exercício {esc(ex.code)} — {esc(ex.title)}</h2>'
        f'<p>{status_badge(sub["status"])} Os campos marcados com * são obrigatórios para enviar.</p></div></div>'
    )
    if ver["version_no"] > 1:
        msg = "Você está preparando uma nova versão. As versões anteriores e seus pareceres continuam no histórico."
        if sub["is_published"]:
            msg += " A versão publicada permanece na biblioteca até que esta nova versão seja aprovada."
        st.info(msg)
        last = next((r for r in det["reviews"] if r["kind"] == C.REVIEW_KIND_AVALIACAO), None)
        if last and last["decision"] == C.DECISION_DEVOLVIDA:
            with st.expander("Observações da última avaliação", expanded=True):
                review_block(p, user, last, key_prefix="ed")

    with st.expander("Enunciado e circuito do exercício", expanded=ver["version_no"] == 1 and not ver["youtube_id"]):
        render_exercise(p, ex, key=f"edit-{ex.id}")

    materials_checklist(ver)

    declared = format_duration(ver["video_duration_s"]) if ver["video_duration_source"] == "declarada" else ""
    with st.form(f"draft-{sid}", border=False):
        with st.container(key="ex-step-video"):
            md('<div class="ex-step"><span>1</span>Vídeo no YouTube *</div>')
            yt = st.text_input("Link do vídeo *", value=ver["youtube_url"] or "", placeholder="https://youtu.be/…")
            dur = st.text_input("Duração do vídeo (mm:ss) *", value=declared, placeholder="7:30",
                                help=f"Recomendado: até {max_min:g} minutos.")
            st.caption(
                "Publique o vídeo no seu próprio canal como **Público** ou **Não listado** (nunca Privado) e mantenha "
                "ativada a opção “Permitir incorporação”. A plataforma não recebe arquivos de vídeo."
            )
        with st.container(key="ex-step-pdf"):
            md('<div class="ex-step"><span>2</span>Arquivo PDF da resolução *</div>')
            up = st.file_uploader(f"PDF da resolução * (até {max_mb:g} MB)", type=["pdf"],
                                  help="Desenvolvimento matemático e conceitual. Arquivo gerado a partir do computador ou do celular.")
            if ver["pdf_key"]:
                st.caption(f"Arquivo salvo: **{ver['pdf_filename']}** · {ver['pdf_pages']} página(s) · "
                           f"{(ver['pdf_size'] or 0) / 1024 / 1024:.1f} MB. Envie outro arquivo apenas para substituí-lo.")
        with st.container(key="ex-step-falstad"):
            md('<div class="ex-step"><span>3</span>Link do circuito no Falstad *</div>')
            fal = st.text_area("Link do circuito *", value=ver["falstad_url"] or "", height=90,
                               placeholder="https://www.falstad.com/circuit/circuitjs.html?ctz=…")
            st.caption("No simulador, use **Arquivo → Exportar como Link** e cole o link completo (não use encurtadores).")
        with st.container(key="ex-step-extra"):
            md('<div class="ex-step"><span>4</span>Informações complementares</div>')
            coaut = st.text_input("Coautores (opcional)", value=sub["coauthors"] or "",
                                  help="Nomes dos colegas que participaram, se a resolução foi feita em grupo.")
            notes = st.text_area("Observações para o avaliador (opcional)", value=ver["student_notes"] or "", height=80)
        with st.container(key="ex-step-send"):
            md('<div class="ex-step"><span>5</span>Revisar e enviar</div>')
            decl = st.checkbox(
                "Declaro que esta resolução é de minha autoria (e dos coautores indicados) e autorizo, caso aprovada, "
                "sua publicação na biblioteca da disciplina com meu nome, o vídeo, o PDF e o circuito."
            )
            b1, b2 = st.columns(2)
            save = b1.form_submit_button("Salvar rascunho", use_container_width=True, icon=":material/save:")
            send = b2.form_submit_button("Salvar e enviar para avaliação", type="primary", use_container_width=True,
                                         icon=":material/send:")

    if save or send:
        data = up.getvalue() if up is not None else None
        if data is not None and hashlib.sha256(data).hexdigest() == ver["pdf_sha256"]:
            data = None  # mesmo arquivo já salvo
        with st.spinner("Salvando…"):
            result, ok = run_action(
                p.submissions.save_draft, user, sid, expected_row_version=sub["row_version"], youtube_url=yt,
                falstad_url=fal, coauthors=coaut, notes=notes, duration_text=dur, pdf_bytes=data,
                pdf_name=up.name if up is not None else None,
            )
        if ok and send:
            with st.spinner("Verificando os materiais e enviando…"):
                warnings, sent = run_action(p.submissions.submit, user, sid,
                                            expected_row_version=result["submission"]["row_version"], declaration=decl)
            if sent:
                flash(f"Resolução do Exercício {ex.code} enviada para avaliação. Acompanhe o estado nesta página.")
                for w in warnings or []:
                    flash(w, "warning")
                go("submissao", id=sid)
            else:
                st.info("O rascunho foi salvo; corrija o item indicado acima e envie novamente.")
        elif ok:
            flash("Rascunho salvo.")
            st.rerun()

    # Revisão dos materiais salvos
    if ver["youtube_id"] or ver["pdf_key"] or ver["falstad_url"]:
        section_head("Conferência", "Revise os materiais salvos", "É exatamente isto que o avaliador verá.")
        c1, c2 = st.columns([1.6, 1], gap="medium")
        with c1:
            if ver["youtube_id"]:
                youtube_embed(ver["youtube_id"])
                st.link_button("Abrir no YouTube", watch_url(ver["youtube_id"]), icon=":material/open_in_new:")
        with c2:
            if ver["falstad_url"]:
                st.link_button("Testar circuito no Falstad", ver["falstad_url"], use_container_width=True,
                               icon=":material/electrical_services:")
            if ver["pdf_key"]:
                if st.toggle("Pré-visualizar PDF salvo", key=f"pvd-{ver['id']}"):
                    try:
                        data, _ = p.submissions.version_pdf(user, ver["id"])
                        pdf_preview(data, f"draft-{ver['id']}")
                    except AppError as exc:
                        st.error(exc.message)

    with st.expander("Descartar este rascunho"):
        first = ver["version_no"] == 1 and sub["first_submitted_at"] is None
        st.caption("A entrega inteira será excluída." if first else
                   f"Somente o rascunho da v{ver['version_no']} será descartado; o histórico é mantido.")
        if st.checkbox("Confirmo o descarte", key=f"disc-ok-{sid}") and st.button("Descartar rascunho", key=f"disc-{sid}"):
            deleted, ok = run_action(p.submissions.discard_draft, user, sid, expected_row_version=sub["row_version"],
                                     success="Rascunho descartado.")
            if ok:
                go("minhas" if deleted else "submissao", **({} if deleted else {"id": sid}))


# --------------------------------------------------------------------------- #
# Alterar Resolução (Minhas Submissões)
# --------------------------------------------------------------------------- #
def mine(p: Platform, user: User) -> None:
    rows = p.submissions.mine(user)
    section_head("Alterar Resolução", "Minhas Submissões",
                 "Acompanhe o estado das entregas, leia os pareceres e prepare novas versões.", count=len(rows))
    if not rows:
        empty_state("Você ainda não iniciou nenhuma entrega", "Escolha um exercício proposto para começar.", "✎")
        st.columns([1, 1, 1])[1].button("Ver Exercícios Propostos", type="primary", use_container_width=True,
                                        on_click=nav_to, args=("propostos",))
        return
    for r in rows:
        with st.container(key=f"ex-mine-{r['id']}"):
            c1, c2 = st.columns([4, 1.3], vertical_alignment="center")
            draft = r["current_state"] == C.V_RASCUNHO and r["status"] != C.RASCUNHO
            c1.markdown(
                f'<div class="ex-prop__code">Exercício {esc(r["code"])} · versão v{r["current_version_no"]}</div>'
                f'<div class="ex-prop__title">{esc(r["title"])}</div>'
                f'<div class="ex-prop__meta">{status_badge(r["status"])}'
                f'{level_badge(r["published_level"]) if r["is_published"] else ""}'
                f'{"<span>rascunho de nova versão em edição</span>" if draft else ""}'
                f'<span>atualizada em {esc(p.fmt(r["updated_at"]))}</span></div>',
                unsafe_allow_html=True,
            )
            c2.button("Abrir", key=f"open-mine-{r['id']}", use_container_width=True,
                      on_click=nav_to, args=("submissao",), kwargs={"id": r["id"]})


def submission(p: Platform, user: User, sid: str | None) -> None:
    st.button("← Minhas Submissões", key="back-mine", on_click=nav_to, args=("minhas",))
    if not sid:
        st.warning("Submissão não informada.")
        return
    det = p.submissions.detail(user, sid)
    sub, cur, ex = det["submission"], det["current"], det["exercise"]
    status = sub["status"]
    md(
        f'<div class="ex-head"><div><div class="ex-head__kicker">{esc(ex.unit)}</div>'
        f'<h2>Exercício {esc(ex.code)} — {esc(ex.title)}</h2>'
        f'<p>{status_badge(status)} {level_badge(sub["published_level"], long=True) if sub["is_published"] else ""}</p></div></div>'
    )
    with st.container(key="ex-status-banner"):
        st.markdown(f"**{C.STATUS_LABELS[status]}.** {C.STATUS_HELP[status]}")
        if status == C.RETIRADA and sub["retired_reason"]:
            st.caption(f"Motivo informado pela administração: {sub['retired_reason']}")

        draft = cur["state"] == C.V_RASCUNHO
        if draft:
            st.button(f"Continuar editando a versão v{cur['version_no']}", type="primary",
                      on_click=nav_to, args=("submeter",), kwargs={"id": sid})
        elif status in C.PENDING_STATUSES:
            with st.expander("Precisa corrigir algo antes da avaliação?"):
                st.caption("Enquanto a análise não começou, você pode cancelar o envio, editar e enviar de novo.")
                if st.button("Cancelar envio e voltar a editar"):
                    _, ok = run_action(p.submissions.withdraw, user, sid, expected_row_version=sub["row_version"],
                                       success="Envio cancelado. A versão voltou a ser rascunho.")
                    if ok:
                        go("submeter", id=sid)
        elif status == C.EM_ANALISE:
            st.caption("Os materiais estão bloqueados durante a avaliação para preservar a integridade do processo.")
        elif status in C.NEW_VERSION_FROM:
            label = "Preparar nova versão" if status != C.APROVADA else "Propor nova versão"
            if status == C.APROVADA:
                st.caption("A versão aprovada continuará publicada. A nova versão só substituirá a publicação após nova aprovação.")
            if st.button(label, type="primary"):
                _, ok = run_action(p.submissions.new_version, user, sid, expected_row_version=sub["row_version"])
                if ok:
                    flash("Nova versão criada com os materiais da anterior. Altere o que for necessário.")
                    go("submeter", id=sid)
        if sub["is_published"]:
            st.button("Ver na biblioteca", on_click=nav_to, args=("resolucao",), kwargs={"r": sid})

    last = next((r for r in det["reviews"] if r["kind"] == C.REVIEW_KIND_AVALIACAO), None)
    if last:
        section_head("Última avaliação", C.LEVEL_LABELS[last["level"]] if last["level"] else C.DEVOLVIDO_LABEL)
        review_block(p, user, last, key_prefix="last")

    section_head("Histórico", "Versões e avaliações", "Nenhuma versão enviada é apagada.", count=len(det["versions"]))
    for v in reversed(det["versions"]):
        when = p.fmt(v["submitted_at"]) if v["submitted_at"] else "não enviada"
        with st.expander(f"Versão v{v['version_no']} — {C.VERSION_LABELS[v['state']]} · {when}",
                         expanded=False):
            cols = st.columns(3)
            if v["youtube_id"]:
                cols[0].link_button("Vídeo no YouTube", watch_url(v["youtube_id"]), use_container_width=True)
            if v["falstad_url"]:
                cols[1].link_button("Circuito no Falstad", v["falstad_url"], use_container_width=True)
            if v["pdf_key"]:
                with cols[2]:
                    lazy_download("PDF desta versão", f"v-{v['id']}", lambda v=v: p.submissions.version_pdf(user, v["id"]))
            if v["video_duration_s"]:
                st.caption(f"Duração do vídeo: {format_duration(v['video_duration_s'])}")
            for rev in [r for r in det["reviews"] if r["version_id"] == v["id"]]:
                review_block(p, user, rev, key_prefix=f"h{v['version_no']}")


__all__ = ["proposed", "submit", "mine", "submission", "lazy_download", "review_block", "parse_youtube_id",
           "clear_public_cache"]
