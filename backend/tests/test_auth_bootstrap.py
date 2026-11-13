"""Auth dependency bootstrap / membership tests."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session, select

from app.core.security import AuthUser
from app.db.models.membership import WorkspaceMembership
from app.db.models.organization import Organization
from app.services.auth import bootstrap_tenant, resolve_principal


def test_bootstrap_creates_owner_membership(session: Session) -> None:
    user = AuthUser(user_id=f"user_{uuid4().hex}", email="a@example.com", claims={})
    principal = bootstrap_tenant(session, user=user)
    assert principal.role == "owner"
    assert principal.user_id == user.user_id

    orgs = list(session.exec(select(Organization)).all())
    assert len(orgs) == 1
    memberships = list(session.exec(select(WorkspaceMembership)).all())
    assert len(memberships) == 1
    assert memberships[0].role == "owner"


def test_resolve_principal_is_idempotent(session: Session) -> None:
    user = AuthUser(user_id=f"user_{uuid4().hex}", email="b@example.com", claims={})
    first = resolve_principal(session, user=user)
    second = resolve_principal(session, user=user)
    assert first.organization_id == second.organization_id
    assert first.workspace_id == second.workspace_id


def test_me_endpoint_returns_principal(client, principal) -> None:
    response = client.get("/api/v1/me")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == principal.user_id
    assert body["role"] == "owner"
    assert body["plan"] == "free"
