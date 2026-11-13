"""Shared pytest fixtures for Atlas backend unit tests."""

from __future__ import annotations

import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-key-for-hs256-unit-tests-only"
os.environ["LANGSMITH_TRACING"] = "false"

from app.api.deps import get_current_principal  # noqa: E402
from app.core.config import reset_settings_cache  # noqa: E402
from app.core.security import AuthUser, Principal  # noqa: E402
from app.db import engine as engine_module  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.db.models import *  # noqa: E402, F403
from app.services.auth import bootstrap_tenant  # noqa: E402


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    yield eng
    # Do not dispose here while other fixtures may still hold Sessions.
    # SQLite StaticPool is process-local and GC is enough for tests.


@pytest.fixture()
def session(engine) -> Iterator[Session]:
    sess = Session(engine)
    try:
        yield sess
    finally:
        sess.close()


@pytest.fixture()
def principal(session: Session) -> Principal:
    user = AuthUser(user_id=f"user_{uuid4().hex}", email="owner@example.com", claims={})
    return bootstrap_tenant(session, user=user, request_id="test")


@pytest.fixture()
def client(engine, principal: Principal) -> Iterator[TestClient]:
    reset_settings_cache()
    application = create_app()

    def override_session() -> Iterator[Session]:
        with Session(engine) as sess:
            yield sess

    def override_principal() -> Principal:
        return principal

    engine_module._engine = engine
    # Lifespan must not dispose the shared StaticPool engine during TestClient exit.
    engine_module.dispose_engine = lambda: None  # type: ignore[assignment]
    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_current_principal] = override_principal

    with TestClient(application) as test_client:
        yield test_client

    application.dependency_overrides.clear()
    engine_module._engine = engine
    reset_settings_cache()
