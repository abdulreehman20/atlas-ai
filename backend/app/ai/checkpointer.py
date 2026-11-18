"""PostgreSQL checkpointer factory for LangChain agent / HITL resume."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_checkpointer(settings: Settings) -> Any | None:
    """Return a PostgresSaver when CHECKPOINT_DATABASE_URL is set, else None.

    Callers must keep the saver for the app lifespan. Use MemorySaver only in tests.
    """

    url = (settings.checkpoint_database_url or "").strip()
    if not url:
        logger.warning("CHECKPOINT_DATABASE_URL unset; agent checkpointer disabled")
        return None
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError:
        logger.warning("langgraph-checkpoint-postgres not installed; checkpointer disabled")
        return None

    # from_conn_string returns a context manager in recent versions; keep open via enter.
    cm = PostgresSaver.from_conn_string(url)
    saver = cm.__enter__()
    return saver


def setup_checkpointer_schema(settings: Settings) -> None:
    """One-time schema setup for checkpoint tables (run from scripts, not per request)."""

    url = (settings.checkpoint_database_url or "").strip()
    if not url:
        raise RuntimeError("CHECKPOINT_DATABASE_URL is required")
    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(url) as checkpointer:
        checkpointer.setup()
