"""Exceções de domínio.

Toda exceção derivada de :class:`AppError` carrega uma mensagem pensada para o
usuário final (em português) e que nunca expõe detalhes internos. Falhas
inesperadas são registradas no log do servidor e apresentadas de forma genérica.
"""

from __future__ import annotations


class AppError(Exception):
    """Erro previsto, com mensagem segura para exibição."""

    def __init__(self, message: str, *, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field


class ValidationError(AppError):
    """Dados informados inválidos ou incompletos."""


class PermissionDenied(AppError):
    """Usuário sem permissão para a operação."""

    def __init__(self, message: str = "Você não tem permissão para realizar esta operação."):
        super().__init__(message)


class NotFound(AppError):
    """Registro inexistente ou não visível para o usuário."""

    def __init__(self, message: str = "Registro não encontrado."):
        super().__init__(message)


class ConflictError(AppError):
    """Alteração concorrente ou transição de estado inválida."""


class AuthError(AppError):
    """Falha de autenticação (mensagem propositalmente genérica)."""


class StorageFailure(AppError):
    """Falha ao gravar ou ler arquivos no armazenamento persistente."""

    def __init__(self, message: str = "Não foi possível acessar o armazenamento de arquivos. Tente novamente em instantes."):
        super().__init__(message)


class ConfigError(AppError):
    """Configuração ausente ou insegura."""
