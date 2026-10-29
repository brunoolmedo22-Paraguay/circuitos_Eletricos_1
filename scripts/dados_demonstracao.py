"""Popula um banco de DEMONSTRAÇÃO com exercícios, alunos e resoluções de exemplo.

    CE1_MODE=demonstracao CE1_DATABASE_URL=sqlite:///.dados_locais/demo.db \
    CE1_STORAGE_BACKEND=local python scripts/dados_demonstracao.py

Recusa-se a rodar fora do modo demonstração: dados de exemplo nunca devem se
misturar aos dados reais de produção. Os vídeos de exemplo usam IDs fictícios
(a miniatura aparece como gradiente e o player informa vídeo indisponível).
"""

from __future__ import annotations

import io
import sys
from urllib.parse import quote

from _comum import load_env_from_secrets

CREDENCIAIS = [
    ("monitor", "Monitor da Disciplina", "admin", "Monitor2026"),
    ("professora", "Professora Responsável", "admin", "Professora2026"),
    ("ana", "Ana Souza", "aluno", "Aluno2026"),
    ("bruno", "Bruno Lima", "aluno", "Aluno2026"),
    ("carla", "Carla Benítez", "aluno", "Aluno2026"),
]

CIRCUITO = (
    "$ 1 0.000005 10.20027730826997 50 5 43 5e-11\n"
    "v 112 368 112 48 0 0 40 12 0 0 0.5\n"
    "r 112 48 400 48 0 1000\n"
    "r 400 48 400 368 0 2000\n"
    "w 400 368 112 368 0\n"
)
FALSTAD = "https://www.falstad.com/circuit/circuitjs.html?cct=" + quote(CIRCUITO, safe="$")

EXERCICIOS = [
    ("1.03", "Lei de Ohm em um resistor", "Unidade 1 — Fundamentos", "lei de Ohm, resistência, corrente",
     "Uma fonte de $12\\,V$ alimenta um resistor de $3\\,k\\Omega$. Determine a corrente e a potência dissipada."),
    ("2.04", "Análise de Malhas", "Unidade 2 — Métodos de Análise", "malhas, LKT, sistemas lineares",
     "Determine as correntes de malha $I_1$ e $I_2$ e a tensão sobre o resistor de $2\\,k\\Omega$."),
    ("5.02", "Carga de um capacitor (RC)", "Unidade 5 — Circuitos RC e RL", "RC, constante de tempo, transitório",
     "Com $R = 10\\,k\\Omega$ e $C = 100\\,\\mu F$, determine $\\tau$ e $v_C(t)$ após o fechamento da chave."),
]


def pdf(title: str, author: str) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for page in (1, 2):
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, 770, title)
        c.setFont("Helvetica", 11)
        c.drawString(72, 748, f"Resolução de exemplo — {author} — página {page}")
        y = 710
        for line in ("1. Identificação das malhas e sentidos de corrente.", "2. Aplicação da LKT em cada malha.",
                     "3. Solução do sistema linear.", "4. Verificação no simulador Falstad."):
            c.drawString(90, y, line)
            y -= 22
        c.showPage()
    c.save()
    return buf.getvalue()


def main() -> int:
    load_env_from_secrets()
    from resolucoes import constants as C
    from resolucoes.config import load_settings
    from resolucoes.services import Platform

    settings = load_settings()
    if not settings.is_demo:
        print("Recusado: este script só roda com [app] mode = \"demonstracao\" (CE1_MODE=demonstracao).")
        return 2

    class Offline:
        status_code = 503

        def json(self):
            return {}

    p = Platform(settings, http_get=lambda *a, **k: Offline())
    if not p.users.bootstrap_needed():
        print("O banco de demonstração já possui dados. Apague o arquivo do banco para recriar.")
        return 1
    import os

    token = settings.bootstrap_token or "token-de-demonstracao-local"
    object.__setattr__(p.settings, "bootstrap_token", token)
    users = {}
    login, name, _, pwd = CREDENCIAIS[0]
    users[login] = p.users.bootstrap_admin(token, login=login, full_name=name, email=None, password=pwd)
    admin = users["monitor"]
    for login, name, role, pwd in CREDENCIAIS[1:]:
        u, _ = p.users.create(admin, login=login, full_name=name, role=role, password=pwd,
                              matricula=None if role == "admin" else f"2026{len(users):03d}")
        from resolucoes import db

        with p.engine.begin() as conn:  # demonstração: dispensa a troca de senha
            conn.execute(db.users.update().where(db.users.c.id == u.id).values(must_change_password=False))
        users[login] = u
    exs = {}
    for code, title, unit, topics, stmt in EXERCICIOS:
        exs[code] = p.exercises.create(admin, code=code, title=title, unit=unit, topics=topics, statement=stmt)

    # Exercícios do pacote Boylestad (Listas 03 e 04) já foram importados automaticamente.
    for ex in p.exercises.list(admin, include_inactive=True):
        exs.setdefault(ex.code, ex)
    good = {k: {"rating": C.RATING_ATENDE, "comment": ""} for k, _ in C.CRITERIA}
    req = {k: True for k, _ in C.REQUIREMENTS}

    def entrega(student, code, video, level=None, devolver=False):
        from resolucoes import db
        import sqlalchemy as sa

        def rv(sid):
            with p.engine.connect() as conn:
                return conn.execute(sa.select(db.submissions.c.row_version).where(db.submissions.c.id == sid)).scalar_one()

        s = users[student]
        sid = p.submissions.start(s, exs[code].id)
        p.submissions.save_draft(s, sid, expected_row_version=rv(sid), youtube_url=f"https://youtu.be/{video}",
                                 falstad_url=FALSTAD, duration_text="6:40",
                                 pdf_bytes=pdf(f"Exercício {code}", s.full_name), pdf_name=f"resolucao_{code}.pdf")
        p.submissions.submit(s, sid, expected_row_version=rv(sid), declaration=True)
        if level or devolver:
            p.reviews.claim(admin, sid, expected_row_version=rv(sid))
        if level:
            p.reviews.approve(admin, sid, expected_row_version=rv(sid), level=level, requirements=req, criteria=good,
                              observations="Explicação clara e circuito coerente com o enunciado.", verified_duration="6:40")
        if devolver:
            crit = dict(good)
            crit["calculos"] = {"rating": C.RATING_NAO_ATENDE, "comment": "Sinal da fonte invertido na malha 2."}
            p.reviews.return_for_correction(admin, sid, expected_row_version=rv(sid), requirements=req, criteria=crit,
                                            problems="A equação da malha 2 considera a fonte com polaridade invertida.",
                                            recommendations="Refaça a LKT na malha 2 e confira o resultado no Falstad.")
        return sid

    entrega("ana", "2.04", "DEMOvid0001", level=C.MUITO_BOM)
    entrega("bruno", "2.04", "DEMOvid0002", level=C.EXCELENTE)
    entrega("carla", "1.03", "DEMOvid0003", level=C.BOM)
    entrega("ana", "3.08", "DEMOvid0004", level=C.EXCELENTE)
    entrega("bruno", "4.17", "DEMOvid0005", devolver=True)
    entrega("carla", "5.02", "DEMOvid0006")

    print("Dados de demonstração criados. Credenciais (somente para teste local):")
    for login, name, role, pwd in CREDENCIAIS:
        print(f"  {role:6} {login:12} senha: {pwd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
