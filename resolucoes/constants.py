"""Vocabulário oficial do módulo Exercícios Resolvidos.

Tudo o que aparece para o usuário (rótulos de estado, níveis, critérios) é
definido aqui, em português brasileiro, para manter a terminologia consistente
entre interface, pareceres em PDF, logs e exportações.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Perfis
# --------------------------------------------------------------------------- #
ROLE_ALUNO = "aluno"
ROLE_ADMIN = "admin"
ROLES = {ROLE_ALUNO: "Aluno", ROLE_ADMIN: "Administrador"}

# --------------------------------------------------------------------------- #
# Estados administrativos da submissão (fluxo formal)
# --------------------------------------------------------------------------- #
RASCUNHO = "RASCUNHO"
SUBMETIDA = "SUBMETIDA"
EM_ANALISE = "EM_ANALISE"
DEVOLVIDA = "DEVOLVIDA"
REENVIADA = "REENVIADA"
APROVADA = "APROVADA"
RETIRADA = "RETIRADA"

STATUS_LABELS = {
    RASCUNHO: "Rascunho",
    SUBMETIDA: "Submetida",
    EM_ANALISE: "Em análise",
    DEVOLVIDA: "Devolvida",
    REENVIADA: "Reenviada",
    APROVADA: "Aprovada",
    RETIRADA: "Retirada",
}

STATUS_HELP = {
    RASCUNHO: "Entrega ainda não enviada. Você pode continuar editando.",
    SUBMETIDA: "Entrega enviada e aguardando avaliação.",
    EM_ANALISE: "Um administrador está avaliando esta versão. Os materiais estão bloqueados.",
    DEVOLVIDA: "A entrega precisa de correções. Consulte o parecer e envie uma nova versão.",
    REENVIADA: "Versão corrigida enviada e aguardando avaliação.",
    APROVADA: "Resolução aprovada e publicada na biblioteca.",
    RETIRADA: "A publicação foi retirada por decisão administrativa.",
}

# Estados em que a versão mais recente aguarda avaliação.
PENDING_STATUSES = (SUBMETIDA, REENVIADA)
# Estados a partir dos quais o aluno pode preparar uma nova versão.
NEW_VERSION_FROM = (DEVOLVIDA, APROVADA, RETIRADA)

# Estado de cada versão individual (imutável depois do envio).
V_RASCUNHO = "RASCUNHO"
V_ENVIADA = "ENVIADA"
V_APROVADA = "APROVADA"
V_DEVOLVIDA = "DEVOLVIDA"

VERSION_LABELS = {
    V_RASCUNHO: "Rascunho",
    V_ENVIADA: "Enviada",
    V_APROVADA: "Aprovada",
    V_DEVOLVIDA: "Devolvida",
}

# --------------------------------------------------------------------------- #
# Níveis oficiais de aprovação — exatamente três. Não há notas nem pontos.
# --------------------------------------------------------------------------- #
EXCELENTE = "EXCELENTE"
MUITO_BOM = "MUITO_BOM"
BOM = "BOM"
LEVELS = (EXCELENTE, MUITO_BOM, BOM)

LEVEL_LABELS = {
    EXCELENTE: "Aprovado — Excelente",
    MUITO_BOM: "Aprovado — Muito Bom",
    BOM: "Aprovado — Bom",
}
LEVEL_SHORT = {EXCELENTE: "Excelente", MUITO_BOM: "Muito Bom", BOM: "Bom"}
LEVEL_DESCRIPTIONS = {
    EXCELENTE: "Resolução correta, completa, muito clara e de qualidade didática sobressalente.",
    MUITO_BOM: "Resolução tecnicamente correta, bem explicada, com oportunidades menores de melhoria.",
    BOM: "Resolução válida que satisfaz os requisitos acadêmicos e apresenta explicação suficientemente compreensível.",
}
# Usado apenas para ordenar o catálogo; não é nota.
LEVEL_ORDER = {EXCELENTE: 0, MUITO_BOM: 1, BOM: 2}

DEVOLVIDO_LABEL = "Devolvido para Correção"

# --------------------------------------------------------------------------- #
# Avaliação qualitativa
# --------------------------------------------------------------------------- #
REQUIREMENTS = (
    ("youtube", "Vídeo no YouTube"),
    ("pdf", "Arquivo PDF da resolução"),
    ("falstad", "Circuito no Falstad"),
)

CRITERIA = (
    ("calculos", "Correção dos cálculos e fundamentos de circuitos elétricos"),
    ("video", "Clareza da explicação em vídeo"),
    ("pdf", "Legibilidade, organização e consistência do PDF"),
    ("falstad", "Funcionamento e correspondência do circuito Falstad"),
    ("coerencia", "Coerência entre os três materiais"),
    ("integridade", "Integridade e originalidade do trabalho"),
)

RATING_ATENDE = "atende"
RATING_PARCIAL = "parcial"
RATING_NAO_ATENDE = "nao_atende"
RATINGS = {
    RATING_ATENDE: "Atende",
    RATING_PARCIAL: "Atende parcialmente",
    RATING_NAO_ATENDE: "Não atende",
}

DECISION_APROVADA = "APROVADA"
DECISION_DEVOLVIDA = "DEVOLVIDA"
DECISION_LABELS = {DECISION_APROVADA: "Aprovada", DECISION_DEVOLVIDA: DEVOLVIDO_LABEL}

REVIEW_KIND_AVALIACAO = "avaliacao"
REVIEW_KIND_AJUSTE = "ajuste_nivel"

# --------------------------------------------------------------------------- #
# Verificação do vídeo
# --------------------------------------------------------------------------- #
VIDEO_OK = "ok"
VIDEO_RESTRITO = "restrito"          # privado ou incorporação desativada
VIDEO_INEXISTENTE = "inexistente"
VIDEO_NAO_VERIFICADO = "nao_verificado"
VIDEO_CHECK_LABELS = {
    VIDEO_OK: "Acessível",
    VIDEO_RESTRITO: "Privado ou com incorporação desativada",
    VIDEO_INEXISTENTE: "Não encontrado",
    VIDEO_NAO_VERIFICADO: "Não verificado automaticamente",
}

# --------------------------------------------------------------------------- #
# Logs
# --------------------------------------------------------------------------- #
LOG_USUARIO = "usuario"
LOG_SUBMISSAO = "submissao"
LOG_AVALIACAO = "avaliacao"
LOG_EXERCICIO = "exercicio"
LOG_SISTEMA = "sistema"
LOG_CATEGORIES = {
    LOG_USUARIO: "Usuários",
    LOG_SUBMISSAO: "Submissões",
    LOG_AVALIACAO: "Avaliações",
    LOG_EXERCICIO: "Exercícios",
    LOG_SISTEMA: "Sistema",
}

# --------------------------------------------------------------------------- #
# Configurações administrativas (valores padrão)
# --------------------------------------------------------------------------- #
DEFAULT_SETTINGS = {
    "max_pdf_mb": 10,
    "max_video_minutes": 8,
    "self_registration_code": "",
    "institution": "Universidade Federal da Integração Latino-Americana — UNILA",
    "course": "Circuitos Elétricos I",
    "semester": "",
    "professor": "",
    "app_url": "",
    "units": [
        "Unidade 1 — Fundamentos",
        "Unidade 2 — Métodos de Análise",
        "Unidade 3 — Teoremas de Redes",
        "Unidade 4 — Capacitores e Indutores",
        "Unidade 5 — Circuitos RC e RL",
    ],
}

HARD_MAX_PDF_MB = 20       # teto absoluto, independente da configuração
MAX_PDF_PAGES = 80
SESSION_COOKIE = "ce1_sessao"
