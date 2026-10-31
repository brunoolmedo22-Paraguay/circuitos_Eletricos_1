"""Validação dos três materiais obrigatórios: YouTube, PDF e Falstad.

A validação aqui garante *presença e formato*; a correção técnica da resolução
é sempre julgada por um administrador.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
from dataclasses import dataclass
from typing import Callable
from urllib.parse import parse_qs, urlparse

from . import constants as C
from .errors import ValidationError

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# YouTube
# --------------------------------------------------------------------------- #
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YT_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
    "youtu.be", "www.youtu.be", "youtube-nocookie.com", "www.youtube-nocookie.com",
}


def parse_youtube_id(url: str) -> str:
    """Extrai o ID de 11 caracteres de qualquer formato usual de link do YouTube."""
    raw = (url or "").strip()
    if not raw:
        raise ValidationError("Informe o link do vídeo no YouTube.", field="youtube")
    if not re.match(r"^https?://", raw, re.I):
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if host not in _YT_HOSTS:
        raise ValidationError(
            "O link informado não é do YouTube. Publique o vídeo no seu canal e cole aqui o link de compartilhamento.",
            field="youtube",
        )
    path_parts = [p for p in parsed.path.split("/") if p]
    candidate = None
    if host.endswith("youtu.be"):
        candidate = path_parts[0] if path_parts else None
    elif path_parts and path_parts[0] in {"shorts", "embed", "live", "v", "e"} and len(path_parts) > 1:
        candidate = path_parts[1]
    elif path_parts[:1] == ["watch"] or not path_parts:
        candidate = (parse_qs(parsed.query).get("v") or [None])[0]
    if not candidate or not _YT_ID.match(candidate):
        if "list=" in parsed.query:
            raise ValidationError("Este é um link de playlist. Informe o link do vídeo específico.", field="youtube")
        if path_parts[:1] and path_parts[0] in {"channel", "c", "user"} or (path_parts and path_parts[0].startswith("@")):
            raise ValidationError("Este é o link de um canal. Informe o link do vídeo específico.", field="youtube")
        raise ValidationError("Não foi possível identificar o vídeo neste link do YouTube.", field="youtube")
    return candidate


def watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def embed_url(video_id: str) -> str:
    # Domínio sem cookies de rastreamento até que o visitante dê play.
    return f"https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1"


def thumbnail_url(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


@dataclass
class VideoCheck:
    status: str
    title: str | None = None
    channel: str | None = None
    duration_s: int | None = None
    detail: str = ""


def parse_iso8601_duration(value: str) -> int | None:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not m:
        return None
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def check_youtube_video(
    video_id: str,
    *,
    api_key: str | None = None,
    http_get: Callable | None = None,
    timeout: float = 6.0,
) -> VideoCheck:
    """Confere se o vídeo é acessível para os avaliadores.

    * Sem chave de API: usa o endpoint público oEmbed (sem custo). Vídeos
      públicos e não listados respondem 200; privados ou com incorporação
      desativada respondem 401/403; inexistentes, 400/404. A duração não é
      informada por esse endpoint.
    * Com chave gratuita da YouTube Data API v3: obtém também duração,
      privacidade e permissão de incorporação.
    * Falhas de rede nunca bloqueiam o aluno: o vídeo fica como "não
      verificado" e o administrador confere na revisão.
    """
    if http_get is None:
        import requests

        http_get = requests.get

    if api_key:
        try:
            resp = http_get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "contentDetails,status,snippet", "id": video_id, "key": api_key},
                timeout=timeout,
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if not items:
                    return VideoCheck(C.VIDEO_INEXISTENTE, detail="Vídeo inexistente ou privado.")
                item = items[0]
                status = item.get("status", {})
                snippet = item.get("snippet", {})
                duration = parse_iso8601_duration(item.get("contentDetails", {}).get("duration", ""))
                if status.get("privacyStatus") == "private":
                    return VideoCheck(C.VIDEO_RESTRITO, detail="Vídeo privado.")
                if status.get("embeddable") is False:
                    return VideoCheck(
                        C.VIDEO_RESTRITO,
                        title=snippet.get("title"),
                        channel=snippet.get("channelTitle"),
                        duration_s=duration,
                        detail="Incorporação desativada.",
                    )
                return VideoCheck(C.VIDEO_OK, snippet.get("title"), snippet.get("channelTitle"), duration)
            log.info("YouTube Data API respondeu HTTP %s; usando oEmbed", resp.status_code)
        except Exception as exc:
            log.info("YouTube Data API indisponível (%s); usando oEmbed", type(exc).__name__)

    try:
        resp = http_get(
            "https://www.youtube.com/oembed",
            params={"url": watch_url(video_id), "format": "json"},
            timeout=timeout,
        )
    except Exception as exc:
        return VideoCheck(C.VIDEO_NAO_VERIFICADO, detail=f"Sem conexão com o YouTube ({type(exc).__name__}).")
    if resp.status_code == 200:
        try:
            data = resp.json()
        except Exception:
            data = {}
        return VideoCheck(C.VIDEO_OK, data.get("title"), data.get("author_name"))
    if resp.status_code in (401, 403):
        return VideoCheck(C.VIDEO_RESTRITO, detail="O YouTube recusou o acesso público ao vídeo.")
    if resp.status_code in (400, 404):
        return VideoCheck(C.VIDEO_INEXISTENTE, detail="O YouTube não encontrou este vídeo.")
    return VideoCheck(C.VIDEO_NAO_VERIFICADO, detail=f"Resposta inesperada do YouTube (HTTP {resp.status_code}).")


def video_check_error(check: VideoCheck) -> str | None:
    """Mensagem bloqueante para o aluno, ou None se o envio pode prosseguir."""
    if check.status == C.VIDEO_INEXISTENTE:
        return "O YouTube não encontrou este vídeo. Confira o link e se o vídeo não foi removido."
    if check.status == C.VIDEO_RESTRITO:
        return (
            "O vídeo não está acessível para os avaliadores. No YouTube Studio, deixe a visibilidade "
            "como Público ou Não listado (nunca Privado) e mantenha ativada a opção “Permitir incorporação”."
        )
    return None


def parse_duration_text(text: str) -> int | None:
    """Converte "m:ss", "mm:ss" ou "h:mm:ss" em segundos. Vazio → None."""
    raw = (text or "").strip()
    if not raw:
        return None
    if not re.fullmatch(r"(\d{1,2}:)?\d{1,2}:\d{2}", raw):
        raise ValidationError("Informe a duração no formato mm:ss (por exemplo, 7:45).", field="duracao")
    parts = [int(p) for p in raw.split(":")]
    if any(p >= 60 for p in parts[1:]):
        raise ValidationError("Duração inválida: minutos e segundos devem ser menores que 60.", field="duracao")
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    if seconds <= 0:
        raise ValidationError("A duração deve ser maior que zero.", field="duracao")
    return seconds


def format_duration(seconds: int | None) -> str:
    if not seconds:
        return ""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# --------------------------------------------------------------------------- #
# Falstad (CircuitJS)
# --------------------------------------------------------------------------- #
_FALSTAD_HOSTS = {"falstad.com", "www.falstad.com", "lushprojects.com", "www.lushprojects.com"}
_FALSTAD_PARAMS = ("ctz", "cct", "startCircuitText", "startCircuitLink", "startCircuit")
_SHORTENERS = {"tinyurl.com", "bit.ly", "goo.gl", "is.gd", "t.ly", "cutt.ly", "shorturl.at", "rb.gy"}


def validate_falstad_url(url: str) -> str:
    """Valida o link do simulador e o devolve exatamente como foi informado.

    O link não é reescrito nem recodificado: os parâmetros ``ctz``/``cct``
    carregam o circuito compactado e qualquer alteração o corromperia.
    """
    raw = (url or "").strip()
    if not raw:
        raise ValidationError("Informe o link do circuito no Falstad.", field="falstad")
    if any(ch.isspace() for ch in raw):
        raise ValidationError("O link do Falstad não pode conter espaços. Copie-o novamente.", field="falstad")
    if not re.match(r"^https?://", raw, re.I):
        raise ValidationError("O link do Falstad deve começar com https://.", field="falstad")
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if host in _SHORTENERS:
        raise ValidationError(
            "Links encurtados não são aceitos. No Falstad, use Arquivo → Exportar como Link e cole o link completo.",
            field="falstad",
        )
    if host not in _FALSTAD_HOSTS or "circuitjs" not in parsed.path.lower():
        raise ValidationError(
            "O link deve apontar para o simulador Falstad (falstad.com/circuit/circuitjs.html).", field="falstad"
        )
    query = parse_qs(parsed.query, keep_blank_values=True)
    present = [p for p in _FALSTAD_PARAMS if query.get(p) and query[p][0].strip()]
    if not present:
        raise ValidationError(
            "Este link abre o simulador vazio, sem o seu circuito. Use Arquivo → Exportar como Link e cole o link gerado.",
            field="falstad",
        )
    if "ctz" in present and len(query["ctz"][0]) < 16:
        raise ValidationError("O link do Falstad parece incompleto (circuito truncado). Copie-o novamente.", field="falstad")
    if len(raw) > 30000:
        raise ValidationError("O link do Falstad é longo demais para ser armazenado.", field="falstad")
    return raw


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
@dataclass
class PdfInfo:
    pages: int
    size: int
    sha256: str


def validate_pdf(data: bytes, *, max_mb: float) -> PdfInfo:
    if not data:
        raise ValidationError("O arquivo PDF está vazio.", field="pdf")
    size = len(data)
    limit = min(float(max_mb), float(C.HARD_MAX_PDF_MB))
    if size > limit * 1024 * 1024:
        raise ValidationError(
            f"O PDF tem {size / 1024 / 1024:.1f} MB e excede o limite de {limit:g} MB. "
            "Comprima as imagens ou exporte com qualidade menor.",
            field="pdf",
        )
    if not data.lstrip()[:5].startswith(b"%PDF-"):
        raise ValidationError("O arquivo enviado não é um PDF válido.", field="pdf")
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            try:
                ok = reader.decrypt("")
            except Exception:
                ok = 0
            if not ok:
                raise ValidationError(
                    "O PDF está protegido por senha. Envie uma versão sem proteção para que possa ser avaliada.",
                    field="pdf",
                )
        pages = len(reader.pages)
        if pages:
            reader.pages[0].mediabox  # força a leitura da primeira página
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("O PDF parece estar corrompido ou incompleto. Gere o arquivo novamente.", field="pdf") from exc
    if pages < 1:
        raise ValidationError("O PDF não possui páginas.", field="pdf")
    if pages > C.MAX_PDF_PAGES:
        raise ValidationError(f"O PDF tem {pages} páginas; o máximo permitido é {C.MAX_PDF_PAGES}.", field="pdf")
    return PdfInfo(pages=pages, size=size, sha256=hashlib.sha256(data).hexdigest())


def safe_filename(name: str, default: str = "resolucao.pdf") -> str:
    base = (name or "").replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^A-Za-z0-9À-ÿ._ -]", "", base).strip(" .")
    if not base:
        base = default
    if not base.lower().endswith(".pdf"):
        base += ".pdf"
    return base[:150]


# --------------------------------------------------------------------------- #
# Exercícios
# --------------------------------------------------------------------------- #
_CODE_RE = re.compile(r"^\d{1,2}\.\d{1,3}[a-z]?$")


def normalize_exercise_code(code: str) -> str:
    raw = (code or "").strip().replace(",", ".").lower()
    if not (_CODE_RE.match(raw) or re.fullmatch(r"a\.\d{2}", raw)):
        raise ValidationError("Código inválido. Use o formato capítulo.número, por exemplo 2.04.", field="codigo")
    return raw


def exercise_sort_key(code: str) -> str:
    if re.fullmatch(r"a\.\d{2}", code):
        return f"999.{int(code.split('.')[1]):04d}"
    m = re.match(r"^(\d+)\.(\d+)([a-z]?)$", code)
    if not m:
        return code
    return f"{int(m.group(1)):03d}.{int(m.group(2)):04d}{m.group(3)}"
