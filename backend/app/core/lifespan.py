"""Application lifespan: shared clients and observability bootstrap."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.ai.checkpointer import build_checkpointer
from app.ai.observability import configure_langsmith
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db import engine as engine_module
from app.db.engine import create_db_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_langsmith(settings)
    engine = create_db_engine(settings)
    app.state.settings = settings
    app.state.engine = engine
    checkpointer = None
    if settings.app_env != "test":
        try:
            checkpointer = build_checkpointer(settings)
        except Exception as exc:
            logger.warning("Checkpointer init skipped: %s", exc)
    app.state.checkpointer = checkpointer
    logger.info("Atlas backend started env=%s", settings.app_env)
    try:
        yield
    finally:
        # Tests share a StaticPool engine via fixtures; disposing it races teardown.
        if settings.app_env != "test":
            engine_module.dispose_engine()
        logger.info("Atlas backend shutdown complete")
