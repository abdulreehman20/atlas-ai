"""Request-scoped database sessions."""

from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session

from app.db.engine import get_engine


def get_session() -> Iterator[Session]:
    engine = get_engine()
    with Session(engine) as session:
        yield session
