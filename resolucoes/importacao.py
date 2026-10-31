"""Importação automática de pacotes de Exercícios Propostos com figuras.

Um *pacote* é uma pasta versionada no repositório, em ``conteudo/pacotes/``,
contendo o arquivo de fichas preparado pelo docente (mesmos campos do
formulário “Novo exercício”), as figuras em PNG e um índice que relaciona cada
figura aos problemas que a utilizam.

Garantias:

* **Fidelidade:** os campos são lidos do arquivo do docente sem reescrita. A
  única adaptação é a linha “Arquivo de apoio da figura … publicar ou anexar”
  dos Materiais de apoio, uma instrução ao docente que a própria importação
  cumpre (a figura passa a ser exibida no exercício).
* **Vínculo exato:** a figura vem do nome de arquivo citado na ficha e é
  conferida contra o índice (lista + número do problema). Nada é deduzido da
  numeração sequencial. Uma figura pode servir a vários exercícios.
* **Idempotência:** cada pacote é aplicado uma única vez por versão (marcador
  no banco). Repetir a operação ou reiniciar a aplicação não duplica nada.
* **Sem sobrescrever o professor:** se o código já existir, o exercício
  cadastrado é mantido; a figura só é anexada se for o mesmo exercício (mesmo
  título) e ele ainda não tiver figuras.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import sqlalchemy as sa

from . import constants as C
from . import db
from .errors import ValidationError
from .services.common import User, audit, require_admin
from .services.exercises import CONTENT_ROOT, FIG_PACOTE
from .validators import normalize_exercise_code

log = logging.getLogger(__name__)

PACKS = [
    {
        "id": "boylestad_12ed_cap8_listas_03_04",
        "nome": "Boylestad, 12ª ed., cap. 8 — Listas 03 e 04",
        "fichas": "Lista_03_04_Carga_Plataforma.txt",
        "indice": "Figuras/INDICE_FIGURAS.txt",
        "figuras": "Figuras",
        "esperado": {"03": 27, "04": 22},
        "somente_ab": {"04": [57, 58, 59, 60]},
    },
    {
        "id": "boylestad_12ed_cap8_listas_03_04",
        "nome": "Boylestad, 12ª ed., cap. 8 — Adicional (15 fichas)",
        "fichas": "Adicional_15_Carga_Plataforma.txt",
        "figuras": "Figuras",
        "esperado": {"AD": 15},
        "indice_auto": True,
        "marcador": "boylestad_12ed_cap8_adicional",
    },
]

FIELDS = [
    ("code", "Código *"),
    ("title", "Título *"),
    ("unit", "Unidade ou tema *"),
    ("topics", "Temas e conceitos (separados por vírgula)"),
    ("statement", "Enunciado *"),
    ("description", "Descrição complementar"),
    ("support_material", "Materiais de apoio (links, referências)"),
    ("available", "Disponível para entregas"),
]
_HEADER = re.compile(
    r"^=+\n((?:LISTA (\d+)|ADICIONAL) \| EXERCÍCIO (\d+) DE (\d+) \| BOYLESTAD: PROBLEMA (\d+))\n=+\n", re.M
)
_FIG_FILE = re.compile(r"Arquivo de apoio da figura:\s*(FIG_[\w.]+?\.png)")
_FIG_NUM = re.compile(r"Figura (\d+\.\d+)")
_INSTRUCAO = re.compile(r"Arquivo de apoio da figura:\s*(FIG_[\w.]+?\.png)\s*\([^)]*\)\.?")


@dataclass
class Ficha:
    lista: str
    seq: int
    total_lista: int
    problema: int
    code: str
    title: str
    unit: str
    topics: str
    statement: str
    description: str
    support_material: str
    available: bool
    figure_file: str
    figure_label: str
    figure_page: str


@dataclass
class Pack:
    id: str
    nome: str
    root: Path
    version: str
    fichas: list[Ficha]
    indice: dict[tuple[str, int], str]  # (lista, problema) → arquivo
    figuras_indice: dict[str, str]       # arquivo → página
    problems: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Leitura
# --------------------------------------------------------------------------- #
def _split_fields(body: str) -> dict[str, str]:
    positions = []
    for key, label in FIELDS:
        m = re.search(r"^" + re.escape(label) + r"[ \t]*$", body, re.M)
        if m is None:
            raise ValidationError(f"Campo ausente: {label}")
        positions.append((m.start(), m.end(), key))
    positions.sort()
    out = {}
    for i, (start, end, key) in enumerate(positions):
        stop = positions[i + 1][0] if i + 1 < len(positions) else len(body)
        out[key] = body[end:stop].strip()
    return out


def parse_fichas(text: str) -> list[Ficha]:
    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    heads = list(_HEADER.finditer(text))
    fichas = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[h.end():end]
        # Remove cabeçalhos de seção (### LISTA 04 ###) que precedem o próximo bloco.
        body = re.split(r"\n#{10,}\n", body)[0]
        f = _split_fields(body)
        mats = f["support_material"]
        mfile = _FIG_FILE.search(mats)
        mnum = _FIG_NUM.search(mats)
        page = re.search(r"p\. (\d+) \(figura\)", mats) or re.search(r"Figura \d+\.\d+, p\. (\d+)", mats)
        fichas.append(
            Ficha(
                lista=f"{int(h.group(2)):02d}" if h.group(2) else "AD", seq=int(h.group(3)), total_lista=int(h.group(4)),
                problema=int(h.group(5)), code=f["code"], title=f["title"], unit=f["unit"], topics=f["topics"],
                statement=f["statement"], description=f["description"],
                support_material=_INSTRUCAO.sub(
                    r"Figura do circuito: \1 — exibida junto ao enunciado nesta plataforma.", mats
                ).strip(),
                available=f["available"].strip().lower() in {"sim", "s", "yes"},
                figure_file=(mfile.group(1) if mfile else
                             (f"FIG_{mnum.group(1).replace('.', '_')}.{'svg' if mnum.group(1) in {'8.97', '8.99', '8.101', '8.103', '8.104', '8.105', '8.106', '8.110'} else 'png'}"
                              if not h.group(2) and mnum else "")),
                figure_label=f"Figura {mnum.group(1)}" if mnum else "",
                figure_page=page.group(1) if page else "",
            )
        )
    return fichas


def parse_indice(text: str) -> tuple[dict[tuple[str, int], str], dict[str, str]]:
    """Linhas no formato ``FIG_8_113.png — Figura 8.113; p. 279; Lista 03: 17; 34, Lista 04: 22``."""
    mapping: dict[tuple[str, int], str] = {}
    pages: dict[str, str] = {}
    for line in text.lstrip("\ufeff").splitlines():
        m = re.match(r"^(FIG_[\w.]+?\.png)\s+—\s+Figura [\d.]+;\s*p\.\s*(\d+);\s*(.+)$", line.strip())
        if not m:
            continue
        fname, page, rest = m.groups()
        pages[fname] = page
        for part in re.finditer(r"Lista (\d+):\s*([\d;\s]+)", rest):
            for num in re.findall(r"\d+", part.group(2)):
                key = (f"{int(part.group(1)):02d}", int(num))
                if key in mapping and mapping[key] != fname:
                    raise ValidationError(f"Índice ambíguo para Lista {key[0]}, problema {key[1]}.")
                mapping[key] = fname
    return mapping, pages


def load_pack(spec: dict, root: Path | None = None) -> Pack:
    base = (root or CONTENT_ROOT) / spec["id"]
    raw = (base / spec["fichas"]).read_bytes()
    fichas = parse_fichas(raw.decode("utf-8-sig"))
    indice, pages = (parse_indice((base / spec["indice"]).read_text(encoding="utf-8-sig"))
                     if not spec.get("indice_auto") else
                     ({(f.lista, f.problema): f.figure_file for f in fichas},
                      {f.figure_file: f.figure_page for f in fichas}))
    pack = Pack(id=spec.get("marcador", spec["id"]), nome=spec["nome"], root=base, version=hashlib.sha256(raw).hexdigest()[:16],
                fichas=fichas, indice=indice, figuras_indice=pages)
    pack.problems = validate_pack(pack, spec)
    return pack


def validate_pack(pack: Pack, spec: dict) -> list[str]:
    """Confere o pacote inteiro. Lista vazia = pacote íntegro."""
    probs: list[str] = []
    counts: dict[str, int] = {}
    seen: set[str] = set()
    for f in pack.fichas:
        counts[f.lista] = counts.get(f.lista, 0) + 1
        where = f"Lista {f.lista}, ficha {f.seq:02d} (problema {f.problema})"
        try:
            code = normalize_exercise_code(f.code)
        except ValidationError:
            probs.append(f"{where}: código inválido '{f.code}'.")
            continue
        if code in seen:
            probs.append(f"{where}: código duplicado {code}.")
        seen.add(code)
        if not code.startswith("a." if f.lista == "AD" else f"{int(f.lista)}."):
            probs.append(f"{where}: código {code} não pertence à lista.")
        for attr in ("title", "unit", "statement"):
            if not getattr(f, attr).strip():
                probs.append(f"{where}: campo obrigatório vazio ({attr}).")
        if f"problema {f.problema}" not in f.title:
            probs.append(f"{where}: o título não cita o problema original.")
        if not f.figure_file:
            probs.append(f"{where}: ficha sem arquivo de figura.")
        elif not (pack.root / spec["figuras"] / f.figure_file).is_file():
            probs.append(f"{where}: figura {f.figure_file} ausente no pacote.")
        expected = pack.indice.get((f.lista, f.problema))
        if expected != f.figure_file:
            probs.append(f"{where}: ficha cita {f.figure_file}, índice indica {expected}.")
        if f.figure_label and f.figure_label not in f.statement and f.figure_label not in f.description:
            probs.append(f"{where}: enunciado não menciona {f.figure_label}.")
        if "Boylestad" not in f.support_material.replace("BOYLESTAD", "Boylestad") or "12. ed" not in f.support_material:
            probs.append(f"{where}: referência bibliográfica incompleta.")
        if f.problema in spec.get("somente_ab", {}).get(f.lista, []):
            items = re.findall(r"^([a-z])\)", f.statement, re.M)
            if items != ["a", "b"]:
                probs.append(f"{where}: deve conter somente os itens a) e b) (encontrado: {items}).")
    for lista, n in spec["esperado"].items():
        if counts.get(lista, 0) != n:
            probs.append(f"Lista {lista}: esperadas {n} fichas, encontradas {counts.get(lista, 0)}.")
    unused = set(pack.figuras_indice) - {f.figure_file for f in pack.fichas}
    if unused:
        probs.append(f"Figuras do índice sem ficha: {sorted(unused)}")
    return probs


# --------------------------------------------------------------------------- #
# Aplicação no banco
# --------------------------------------------------------------------------- #
def spec_path(pack: Pack) -> str:
    return pack.root.name


def _marker_key(pack_id: str) -> str:
    return f"_pacote:{pack_id}"


def pack_status(platform, pack_id: str) -> dict | None:
    with platform.engine.connect() as conn:
        row = conn.execute(sa.select(db.app_settings.c.value_json)
                           .where(db.app_settings.c.key == _marker_key(pack_id))).first()
    return json.loads(row[0]) if row else None


def apply_pack(platform, pack: Pack, *, actor: User | None = None) -> dict:
    """Cadastra as fichas ausentes e vincula as figuras (transação única)."""
    if pack.problems:
        raise ValidationError("Pacote com inconsistências: " + "; ".join(pack.problems[:5]))
    from PIL import Image

    svc = platform.exercises
    criados, completados, mantidos = [], [], []
    with platform.engine.begin() as conn:
        for f in pack.fichas:
            code = normalize_exercise_code(f.code)
            rel = f"{spec_path(pack)}/Figuras/{f.figure_file}" if f.figure_file else ""
            if f.figure_file.endswith(".svg"):
                import xml.etree.ElementTree as ET
                svg = ET.parse(pack.root / "Figuras" / f.figure_file).getroot()
                w, h = int(svg.attrib["width"]), int(svg.attrib["height"])
            elif f.figure_file:
                with Image.open(pack.root / "Figuras" / f.figure_file) as im:
                    w, h = im.size
            else:
                w, h = None, None
            caption = f"Boylestad, 12ª ed., cap. 8, p. {f.figure_page or pack.figuras_indice.get(f.figure_file, '')}".rstrip(", p. ")
            existing = conn.execute(sa.select(db.exercises.c.id, db.exercises.c.title)
                                    .where(db.exercises.c.code == code)).first()
            if existing is not None:
                has_figs = conn.execute(sa.select(sa.func.count()).select_from(db.exercise_figures)
                                        .where(db.exercise_figures.c.exercise_id == existing.id)).scalar_one()
                if f.figure_file and existing.title.strip() == f.title.strip() and not has_figs:
                    svc._attach(conn, existing.id, source=FIG_PACOTE, ref=rel, label=f.figure_label,
                                caption=caption, width=w, height=h)
                    completados.append(code)
                else:
                    mantidos.append(code)
                if pack.id == "boylestad_12ed_cap8_adicional" and existing.title.strip() == f.title.strip() and f.available:
                    conn.execute(db.exercises.update().where(db.exercises.c.id == existing.id).values(active=True, updated_at=db.utcnow()))
                continue
            data = svc._clean(title=f.title, statement=f.statement, unit=f.unit, topics=f.topics,
                              description=f.description, support_material=f.support_material)
            eid = svc._insert(conn, code, data, active=f.available, actor_id=actor.id if actor else None)
            if f.figure_file:
                svc._attach(conn, eid, source=FIG_PACOTE, ref=rel, label=f.figure_label, caption=caption, width=w, height=h)
            criados.append(code)
        report = {
            "pacote": pack.nome,
            "versao": pack.version,
            "aplicado_em_utc": db.utcnow().isoformat(timespec="seconds"),
            "fichas": len(pack.fichas),
            "criados": criados,
            "figuras_completadas": completados,
            "mantidos_sem_alteracao": mantidos,
        }
        payload = json.dumps(report, ensure_ascii=False)
        key = _marker_key(pack.id)
        if conn.execute(db.app_settings.update().where(db.app_settings.c.key == key)
                        .values(value_json=payload, updated_at=db.utcnow(), updated_by=actor.id if actor else None)).rowcount == 0:
            conn.execute(db.app_settings.insert().values(key=key, value_json=payload, updated_at=db.utcnow(),
                                                         updated_by=actor.id if actor else None))
        audit(conn, C.LOG_EXERCICIO, "pacote_importado", actor, actor_login=None if actor else "importacao-automatica",
              target_type="pacote", summary=f"{pack.nome}: {len(criados)} criado(s), {len(completados)} figura(s) "
              f"vinculada(s) a existentes, {len(mantidos)} código(s) mantido(s)", mantidos=mantidos)
    return report


def ensure_packs(platform, *, root: Path | None = None) -> list[dict]:
    """Executado na inicialização: aplica cada pacote uma vez por versão."""
    reports = []
    for spec in PACKS:
        if not ((root or CONTENT_ROOT) / spec["id"]).is_dir():
            continue
        try:
            pack = load_pack(spec, root)
            status = pack_status(platform, pack.id)
            if status and status.get("versao") == pack.version:
                continue
            reports.append(apply_pack(platform, pack))
            log.info("Pacote %s importado", pack.id)
        except sa.exc.IntegrityError:
            log.info("Pacote %s importado por outra instância em paralelo", spec["id"])
        except Exception:
            log.exception("Falha ao importar o pacote %s (a aplicação continua funcionando)", spec["id"])
    return reports


def reimport(platform, actor: User, pack_id: str) -> dict:
    """Ação administrativa: recria apenas os exercícios ausentes do pacote."""
    require_admin(actor)
    spec = next(s for s in PACKS if s.get("marcador", s["id"]) == pack_id)
    return apply_pack(platform, load_pack(spec), actor=actor)
