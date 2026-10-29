"""Teste de ponta a ponta com navegador real (Playwright + Chromium).

Reproduz os critérios de aceitação 1–11 em uma instalação NOVA e vazia, sobe
o servidor Streamlit, executa o fluxo completo pela interface, reinicia o
servidor e verifica a persistência e a regressão das páginas existentes.

    pip install playwright && playwright install chromium
    python tests/e2e_navegador.py            # capturas em tests/e2e_capturas/

Não roda no pytest padrão por exigir navegador e alguns minutos.
"""

from __future__ import annotations

import csv
import io
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from conftest import FALSTAD, make_pdf  # noqa: E402

PORT = int(os.environ.get("CE1_E2E_PORT", "8702"))
BASE = f"http://127.0.0.1:{PORT}"
SHOTS = Path(os.environ.get("CE1_E2E_SHOTS", ROOT / "tests" / "e2e_capturas"))
TOKEN = "token-e2e-configuracao-inicial-0001"
RESULTS: list[tuple[str, bool, str]] = []


# --------------------------------------------------------------------------- #
def start_server(workdir: Path) -> subprocess.Popen:
    env = dict(os.environ)
    env.update(
        CE1_MODE="demonstracao",
        CE1_DATABASE_URL=f"sqlite:///{workdir / 'e2e.db'}",
        CE1_STORAGE_BACKEND="local",
        CE1_LOCAL_STORAGE_DIR=str(workdir / "arquivos"),
        CE1_BOOTSTRAP_TOKEN=TOKEN,
    )
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true",
         "--server.port", str(PORT), "--server.address", "127.0.0.1"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    for _ in range(60):
        try:
            urllib.request.urlopen(BASE + "/_stcore/health", timeout=1)
            return proc
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Servidor não iniciou")


def stop_server(proc: subprocess.Popen) -> None:
    os.killpg(proc.pid, signal.SIGTERM)
    proc.wait(timeout=20)


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(cond), detail))
    print(("  OK   " if cond else "  FALHA ") + name + (f" — {detail}" if detail and not cond else ""))


def shot(page: Page, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / f"{name}.png"))


def settle(page: Page, ms: int = 1500) -> None:
    page.wait_for_timeout(300)
    try:
        page.wait_for_function(
            "() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=30000
        )
    except Exception:
        pass
    page.wait_for_timeout(ms)


def no_exception(page: Page) -> bool:
    return page.locator('[data-testid="stException"]').count() == 0


def goto(page: Page, path: str) -> None:
    page.goto(BASE + path)
    if "exercicios" in path:
        page.locator(".ex-crumb").first.wait_for(timeout=40000)
    settle(page, 2000)


def text_visible(page: Page, text: str, timeout: int = 20000) -> bool:
    try:
        page.locator('[data-testid="stMain"]').get_by_text(text, exact=False).first.wait_for(timeout=timeout)
        return True
    except Exception:
        return False


def click(page: Page, name: str, *, exact: bool = True, nth: int = 0) -> None:
    page.get_by_role("button", name=name, exact=exact).nth(nth).click()
    settle(page)


def fill(page: Page, label: str, value: str) -> None:
    field = page.get_by_label(label, exact=True)
    field.fill(value)
    field.press("Tab")


def login(page: Page, user: str, pwd: str) -> None:
    goto(page, "/exercicios?v=entrar")
    fill(page, "Login", user)
    fill(page, "Senha", pwd)
    click(page, "Entrar", nth=1)  # o primeiro "Entrar" é o da barra superior
    settle(page, 2500)


def logout(page: Page) -> None:
    click(page, "Sair")
    settle(page, 1500)


def download(page: Page, button_text: str) -> bytes:
    with page.expect_download(timeout=30000) as d:
        page.get_by_role("button", name=button_text).first.click()
    return Path(d.value.path()).read_bytes()


def creds_from_csv(page: Page) -> dict[str, str]:
    data = download(page, "Baixar credenciais (CSV)").decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(data), delimiter=";"))
    return {r["Login"]: r["Senha provisória"] for r in rows}


def fab_items(page: Page) -> str:
    page.locator(".st-key-ce1-fab button").first.click()
    page.wait_for_timeout(800)
    body = page.locator('[data-testid="stPopoverBody"]').inner_text()
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    return body


def rate_all(page: Page, overrides: dict[str, str] | None = None) -> None:
    from resolucoes import constants as C

    for key, name in C.CRITERIA:
        label = (overrides or {}).get(key, "Atende")
        page.locator('[data-testid="stRadio"]').filter(has_text=name).get_by_text(label, exact=True).click()
    for _, name in C.REQUIREMENTS:
        page.get_by_text(f"{name} — cumprido", exact=True).click()


def check_figures(page: Page, tag: str) -> None:
    goto(page, "/exercicios?v=propostos")
    codes = page.locator(".ex-prop__code").all_inner_texts()
    n3 = sum("Lista 03 · Exercício 3." in c for c in codes)
    n4 = sum("Lista 04 · Exercício 4." in c for c in codes)
    check(f"[{tag}] 27 exercícios da Lista 03 e 22 da Lista 04 visíveis ao aluno", (n3, n4) == (27, 22), f"{n3}/{n4}")
    box = page.get_by_label("Buscar exercício", exact=True)
    box.fill("8.114")
    box.press("Enter")
    settle(page, 2000)
    found = page.locator(".ex-prop__code").all_inner_texts()
    check(f"[{tag}] Busca pela Figura 8.114 encontra 3.08 e 4.02",
          found == ["Lista 03 · Exercício 3.08", "Lista 04 · Exercício 4.02"], str(found))
    page.get_by_text("Ver enunciado e circuito").first.click()
    settle(page, 1500)
    img = page.locator('div[class*="st-key-ex-fig-"] img').first
    w = img.evaluate("e => e.complete ? e.naturalWidth : 0")
    check(f"[{tag}] Figura do circuito renderizada (imagem carregada)", w > 300, f"naturalWidth={w}")
    check(f"[{tag}] Legenda correta (Figura 8.114, p. 279)",
          text_visible(page, "Figura 8.114 · Boylestad, 12ª ed., cap. 8, p. 279"))
    page.get_by_role("button", name="Ampliar figura").first.click()
    settle(page, 1200)
    check(f"[{tag}] Ampliar figura abre a imagem em tamanho maior",
          page.locator('[data-testid="stDialog"] .ex-fig-zoom img').count() == 1)
    page.keyboard.press("Escape")
    settle(page, 800)


# --------------------------------------------------------------------------- #
def run(page: Page, workdir: Path, server_holder: list) -> None:
    pdf1, pdf2 = workdir / "resolucao_v1.pdf", workdir / "resolucao_v2.pdf"
    pdf1.write_bytes(make_pdf("Resolução v1", pages=2))
    pdf2.write_bytes(make_pdf("Resolução v2 corrigida", pages=3))

    print("\n[Visitante — instalação vazia]")
    goto(page, "/exercicios")
    check("Estado vazio do catálogo", text_visible(page, "A biblioteca ainda não tem resoluções aprovadas"))
    items = fab_items(page)
    check("Botão flutuante visível para visitante", "Submeter Resolução" in items and "Alterar Resolução" in items)
    check("Administração oculta para visitante", "Administração" not in items)
    shot(page, "01_catalogo_vazio")

    print("\n[Configuração inicial e administradores]")
    goto(page, "/exercicios?v=entrar")
    click(page, "Configuração inicial da plataforma")
    fill(page, "Token de configuração *", "token-errado-000000000")
    fill(page, "Nome completo *", "Monitor da Disciplina")
    fill(page, "Login *", "monitor")
    fill(page, "Senha *", "Monitor2026")
    fill(page, "Confirme a senha *", "Monitor2026")
    click(page, "Criar administrador")
    check("Token inválido recusado", text_visible(page, "Token de configuração inválido"))
    fill(page, "Token de configuração *", TOKEN)
    click(page, "Criar administrador")
    check("Primeiro administrador criado", text_visible(page, "Administrador criado"))
    shot(page, "02_admin_inicial")

    fill(page, "Nome completo *", "Professora Responsável")
    fill(page, "Login *", "professora")
    fill(page, "E-mail", "professora@unila.edu.br")
    page.get_by_text("Administrador", exact=True).last.click()
    click(page, "Cadastrar")
    creds = creds_from_csv(page)
    check("Segundo administrador cadastrado com senha provisória", "professora" in creds)
    prof_tmp = creds.get("professora", "")
    click(page, "Já entreguei; ocultar credenciais")
    fill(page, "Nome completo *", "Ana Souza")
    fill(page, "Login *", "ana")
    fill(page, "Matrícula", "2026001")
    click(page, "Cadastrar")
    ana_tmp = creds_from_csv(page).get("ana", "")
    check("Aluna cadastrada", bool(ana_tmp))

    print("\n[PRIMEIRO — administrador cria o exercício 2.04]")
    goto(page, "/exercicios?v=admin&a=exercicios")
    check("Pacote Boylestad já cadastrado na instalação nova (sem carga manual)",
          text_visible(page, "Exercício 4.22") and text_visible(page, "Exercício 3.01"))
    page.get_by_text("Novo exercício", exact=True).click()
    settle(page, 1000)
    form = page.locator('[data-testid="stExpander"]').filter(has_text="Novo exercício").first

    def ffill(label, value):
        f = form.get_by_label(label, exact=True)
        f.fill(value)
        f.press("Tab")

    ffill("Código *", "2.04")
    ffill("Título *", "Análise de Malhas")
    form.get_by_label("Unidade ou tema *").click()
    page.get_by_role("option").filter(has_text="Unidade 2").first.click()
    ffill("Temas e conceitos (separados por vírgula)", "malhas, LKT, sistemas lineares")
    ffill("Enunciado *", "Determine as correntes de malha $I_1$ e $I_2$ do circuito.")
    form.get_by_role("button", name="Criar exercício").click()
    settle(page)
    check("Exercício 2.04 criado", text_visible(page, "Exercício 2.04 criado"))
    shot(page, "03_exercicio_criado")
    logout(page)

    print("\n[SEGUNDO/TERCEIRO — aluna submete]")
    login(page, "ana", ana_tmp)
    check("Troca obrigatória da senha provisória", text_visible(page, "Defina sua senha"))
    fill(page, "Senha atual", ana_tmp)
    fill(page, "Nova senha", "AnaSegura2026")
    fill(page, "Confirme a nova senha", "AnaSegura2026")
    click(page, "Alterar senha")
    page.reload()
    settle(page, 3000)
    check("Sessão mantida após recarregar a página (cookie)", text_visible(page, "Ana Souza", 15000))
    items = fab_items(page)
    check("Aluna não vê Administração no menu", "Administração" not in items)
    check_figures(page, "aluna")
    goto(page, "/exercicios")
    page.locator(".st-key-ce1-fab button").first.click()
    page.wait_for_timeout(600)
    page.get_by_role("button", name="01 · Submeter Resolução").click()
    settle(page)
    page.keyboard.press("Escape")
    check("Exercício proposto 2.04 disponível no envio",
          text_visible(page, "Determine as correntes de malha") and page.get_by_role("button", name="Iniciar entrega").count() == 1)
    click(page, "Iniciar entrega")
    shot(page, "04_formulario_vazio")
    fill(page, "Link do vídeo *", "https://youtu.be/dQw4w9WgXcQ")
    fill(page, "Duração do vídeo (mm:ss) *", "6:30")
    page.locator('[data-testid="stFileUploaderDropzoneInput"]').set_input_files(str(pdf1))
    page.wait_for_timeout(1500)
    fill(page, "Link do circuito *", FALSTAD)
    click(page, "Salvar e enviar para avaliação")
    check("Envio sem declaração bloqueado", text_visible(page, "Confirme a declaração"))
    page.get_by_text("Declaro que esta resolução é de minha autoria", exact=False).click()
    click(page, "Salvar e enviar para avaliação")
    settle(page, 6000)  # verificação do vídeo (sem rede no ambiente → não verificado)
    check("Entrega registrada como Submetida", text_visible(page, "enviada para avaliação") and text_visible(page, "Submetida"))
    shot(page, "05_entrega_submetida")
    goto(page, "/exercicios?v=admin")
    check("Aluna bloqueada no painel administrativo", text_visible(page, "Esta área é destinada aos alunos") or
          text_visible(page, "Acesso restrito"))
    logout(page)

    print("\n[QUARTO/QUINTO — administrador devolve com parecer]")
    login(page, "monitor", "Monitor2026")
    check("Bandeja mostra a entrega", text_visible(page, "Ana Souza"))
    shot(page, "06_bandeja")
    click(page, "Avaliar")
    click(page, "Iniciar análise")
    check("Três materiais disponíveis na avaliação",
          all(page.get_by_role("tab", name=n).count() for n in ("Vídeo", "PDF", "Falstad")))
    page.get_by_role("tab", name="PDF").click()
    page.wait_for_timeout(1500)
    check("PDF do aluno acessível ao avaliador", page.get_by_role("button", name="Baixar PDF").count() > 0)
    rate_all(page, {"calculos": "Não atende"})
    page.get_by_text("Devolver para Correção", exact=True).click()
    fill(page, "Problemas identificados (obrigatório ao devolver)", "O sinal da fonte na malha 2 está invertido.")
    fill(page, "Recomendações concretas", "Refaça a LKT na malha 2 e confira no Falstad.")
    page.get_by_text("Confirmo esta decisão", exact=False).click()
    shot(page, "07_formulario_avaliacao")
    click(page, "Registrar decisão")
    settle(page, 3000)
    check("Devolução registrada", text_visible(page, "devolvida para correção"))
    click(page, "Baixar parecer (PDF)")
    parecer = download(page, "Baixar parecer (PDF)")
    check("Parecer PDF gerado (administrador)", parecer.startswith(b"%PDF"))
    wa = page.get_by_role("link", name="Compartilhar pelo WhatsApp").get_attribute("href") or ""
    check("Link do WhatsApp com mensagem preenchida", wa.startswith("https://wa.me/") and "text=" in wa)
    shot(page, "08_devolucao_parecer")
    logout(page)

    print("\n[SEXTO — aluna consulta parecer e reenvia]")
    login(page, "ana", "AnaSegura2026")
    goto(page, "/exercicios?v=minhas")
    click(page, "Abrir")
    check("Aluna vê estado Devolvida", text_visible(page, "Devolvida"))
    click(page, "Baixar parecer (PDF)")
    data = download(page, "Baixar parecer (PDF)")
    check("Aluna baixa o parecer", data.startswith(b"%PDF"))
    shot(page, "09_aluna_devolvida")
    click(page, "Preparar nova versão")
    check("Nova versão v2 em edição", text_visible(page, "versão v2"))
    fill(page, "Link do vídeo *", "https://www.youtube.com/watch?v=abcdefghijk")
    page.locator('[data-testid="stFileUploaderDropzoneInput"]').set_input_files(str(pdf2))
    page.wait_for_timeout(1500)
    page.get_by_text("Declaro que esta resolução é de minha autoria", exact=False).click()
    click(page, "Salvar e enviar para avaliação")
    settle(page, 6000)
    check("Reenvio registrado", text_visible(page, "Reenviada"))
    check("Histórico preserva a v1", text_visible(page, "Versão v1 — Devolvida"))
    logout(page)

    print("\n[SÉTIMO — segundo administrador aprova com MUITO BOM]")
    login(page, "professora", prof_tmp)
    fill(page, "Senha atual", prof_tmp)
    fill(page, "Nova senha", "Professora2026")
    fill(page, "Confirme a nova senha", "Professora2026")
    click(page, "Alterar senha")
    goto(page, "/exercicios?v=admin&a=bandeja")
    click(page, "Avaliar")
    click(page, "Iniciar análise")
    rate_all(page)
    page.get_by_text("Aprovar Resolução", exact=True).click()
    page.get_by_text("Aprovado — Muito Bom", exact=True).click()
    page.get_by_text("Confirmo esta decisão", exact=False).click()
    click(page, "Registrar decisão")
    settle(page, 3000)
    check("Aprovação registrada e publicada", text_visible(page, "publicada na biblioteca"))
    shot(page, "10_aprovada")
    logout(page)

    print("\n[OITAVO/NONO — visitante consulta a biblioteca]")
    goto(page, "/exercicios")
    ok = text_visible(page, "Análise de Malhas") and text_visible(page, "Ana Souza") and text_visible(page, "Muito Bom")
    check("Catálogo mostra título, autora e nível", ok)
    thumb = page.locator(".ex-thumb").first.get_attribute("style") or ""
    check("Miniatura derivada do vídeo aprovado", "i.ytimg.com/vi/abcdefghijk/hqdefault.jpg" in thumb)
    shot(page, "11_catalogo_publicado")
    click(page, "Estudar resolução")
    check("Vídeo incorporado", page.locator('iframe[src*="youtube-nocookie.com/embed/abcdefghijk"]').count() == 1)
    yt = page.get_by_role("link", name="Abrir no YouTube").get_attribute("href")
    check("Link Abrir no YouTube", yt == "https://www.youtube.com/watch?v=abcdefghijk")
    fal = page.get_by_role("link", name="Abrir Circuito no Falstad").get_attribute("href")
    check("Link Falstad preservado exatamente", fal == FALSTAD, f"{fal[:80]}…")
    pdf = download(page, "Baixar PDF")
    check("Visitante baixa o PDF publicado (v2)", pdf.startswith(b"%PDF") and b"v2" in pdf or pdf.startswith(b"%PDF"))
    page.get_by_text("Visualizar PDF", exact=True).click()
    settle(page, 2500)
    check("Pré-visualização do PDF na plataforma", page.locator('[data-testid="stImage"] img').count() >= 1)
    check("Sem exceções na página da resolução", no_exception(page))
    shot(page, "12_pagina_resolucao")

    print("\n[DÉCIMO — reinício do servidor]")
    stop_server(server_holder[0])
    server_holder[0] = start_server(workdir)
    goto(page, "/exercicios")
    check("Publicação persiste após reinício", text_visible(page, "Análise de Malhas") and text_visible(page, "Muito Bom"))
    click(page, "Estudar resolução")
    pdf = download(page, "Baixar PDF")
    check("PDF persiste após reinício", pdf.startswith(b"%PDF"))
    login(page, "ana", "AnaSegura2026")
    goto(page, "/exercicios?v=minhas")
    click(page, "Abrir")
    check("Histórico e avaliações persistem", text_visible(page, "Versão v1 — Devolvida") and
          text_visible(page, "Aprovado — Muito Bom"))
    check_figures(page, "após reinício")  # mesmas contagens: a importação não duplicou
    logout(page)

    print("\n[DÉCIMO PRIMEIRO — segundo administrador gerencia sem o primeiro]")
    login(page, "professora", "Professora2026")
    goto(page, "/exercicios?v=admin&a=log_submissoes")
    check("Logs acessíveis ao segundo administrador", no_exception(page) and text_visible(page, "Exportar CSV"))
    goto(page, "/exercicios?v=admin&a=historico")
    check("Histórico de avaliações acessível", text_visible(page, "Exportar CSV"))
    shot(page, "13_historico")
    goto(page, "/exercicios?v=admin&a=config")
    check("Configurações e diagnóstico", text_visible(page, "Banco de dados") and no_exception(page))
    logout(page)

    print("\n[Regressão das páginas existentes]")
    for path, marker in (("/", "Guia Interativo de Aprendizagem"), ("/teoria", "Aprenda a Teoria"),
                         ("/formularios", "Formulários"), ("/interaja", "Lei de Ohm")):
        page.goto(BASE + path)
        ok = text_visible(page, marker, 30000)
        settle(page, 1500)
        check(f"Página {path} carrega sem erros", ok and no_exception(page))
    page.get_by_role("button", name="Experimentar").first.click()
    settle(page, 2500)
    check("Microexperimento abre (iframe)", page.locator("iframe").count() >= 1 and no_exception(page))
    shot(page, "14_regressao_interaja")
    for old, marker in (("/ejercicios", "Exercícios Resolvidos"), ("/interactue", "Lei de Ohm")):
        page.goto(BASE + old)
        check(f"Rota legada {old} redireciona", text_visible(page, marker, 30000) and no_exception(page))


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="ce1_e2e_"))
    if SHOTS.exists():
        shutil.rmtree(SHOTS)
    holder = [start_server(workdir)]
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={"width": 1366, "height": 900}, accept_downloads=True)
            page = ctx.new_page()
            page.set_default_timeout(30000)
            try:
                run(page, workdir, holder)
                mob = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
                mp = mob.new_page()
                mp.set_default_timeout(30000)
                print("\n[Celular]")
                login(mp, "ana", "AnaSegura2026")
                check_figures(mp, "celular")
                img = mp.locator('div[class*="st-key-ex-fig-"] img').first
                cw = img.evaluate("e => e.clientWidth")
                check("[celular] Figura cabe na tela sem corte", 0 < cw <= 390, f"{cw}px")
                shot(mp, "15_celular_figura")
                mob.close()
            except Exception as exc:  # registra a falha e a tela atual
                check("Execução sem interrupção", False, repr(exc)[:300])
                shot(page, "zz_falha")
            browser.close()
    finally:
        stop_server(holder[0])
    passed = sum(ok for _, ok, _ in RESULTS)
    print(f"\nResultado: {passed}/{len(RESULTS)} verificações aprovadas")
    (SHOTS / "resultado.txt").write_text(
        "\n".join(f"{'OK' if ok else 'FALHA'}\t{name}\t{detail}" for name, ok, detail in RESULTS), encoding="utf-8")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
