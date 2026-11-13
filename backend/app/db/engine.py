"""SQLAlchemy/SQLModel engine factory."""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import create_engine

from app.core.config import Settings

_engine: Engine | None = None


def create_db_engine(settings: Settings, *, force: bool = False) -> Engine:
    global _engine
    if _engine is not None and not force:
        return _engine
    connect_args: dict[str, object] = {}
    url = settings.database_url
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    _engine = create_engine(
        url,
        echo=settings.app_env == "development",
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database engine is not initialized")
    return _engine


def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
