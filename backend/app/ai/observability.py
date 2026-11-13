"""LangSmith tracing configuration."""

from __future__ import annotations

import os

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def configure_langsmith(settings: Settings) -> None:
    if not settings.langsmith_tracing:
        os.environ.pop("LANGSMITH_TRACING", None)
        return

    os.environ["LANGSMITH_TRACING"] = "true"
    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_project:
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    logger.info("LangSmith tracing enabled project=%s", settings.langsmith_project)
