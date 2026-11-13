"""Application lifespan: shared clients and observability bootstrap."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.ai.observability import configure_langsmith
from app.core.config import Settings, get_settings
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
    logger.info("Atlas backend started env=%s", settings.app_env)
    try:
        yield
    finally:
        # Tests share a StaticPool engine via fixtures; disposing it races teardown.
        if settings.app_env != "test":
            engine_module.dispose_engine()
        logger.info("Atlas backend shutdown complete")


def apply_langsmith_env(settings: Settings) -> None:
    """Expose LangSmith env vars for LangChain auto-instrumentation."""
    if settings.langsmith_tracing:
        os.environ["LANGSMITH_TRACING"] = "true"
        if settings.langsmith_api_key:
            os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        if settings.langsmith_project:
            os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
