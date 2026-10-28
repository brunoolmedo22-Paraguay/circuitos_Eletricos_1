"""Camada de serviços (independente do Streamlit, testável isoladamente).

Toda regra de permissão é verificada aqui, no servidor. A interface apenas
apresenta o resultado: esconder um botão nunca é a única proteção.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    from backports.zoneinfo import ZoneInfo  # type: ignore

from .. import db
from ..config import Settings
from ..errors import ConfigError
from ..storage import FileStore, build_store
from .admin import AdminService
from .catalog import CatalogService
from .common import User
from .exercises import Exercise, ExerciseService
from .reviews import ReviewService
from .submissions import SubmissionService
from .users import UserService

__all__ = ["Platform", "User", "Exercise"]


class Platform:
    def __init__(
        self,
        settings: Settings,
        *,
        engine=None,
        store: FileStore | None = None,
        http_get: Callable | None = None,
        init: bool = True,
    ):
        if not settings.database_url and engine is None:
            raise ConfigError("Banco de dados não configurado.")
        self.settings = settings
        self.engine = engine or db.get_engine(settings.database_url)
        self.store = store or build_store(settings, self.engine)
        self.http_get = http_get
        try:
            self.tz = ZoneInfo("America/Sao_Paulo")
        except Exception:  # pragma: no cover - sem base tz no sistema
            self.tz = timezone.utc
        self.admin = AdminService(self)
        self.users = UserService(self)
        self.exercises = ExerciseService(self)
        self.submissions = SubmissionService(self)
        self.reviews = ReviewService(self)
        self.catalog = CatalogService(self)
        if init:
            db.init_schema(self.engine)

    def local(self, dt: datetime | None) -> datetime | None:
        """Converte um instante UTC armazenado para o horário de Brasília."""
        if dt is None:
            return None
        return dt.replace(tzinfo=timezone.utc).astimezone(self.tz)

    def fmt(self, dt: datetime | None, with_time: bool = True) -> str:
        loc = self.local(dt)
        if loc is None:
            return "—"
        return loc.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")
