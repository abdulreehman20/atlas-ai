"""Invite accept joins existing workspace instead of bootstrapping a new org."""

from __future__ import annotations

from uuid import uuid4

from sqlmodel import Session, select

from app.core.security import AuthUser
from app.db.models.enums import MembershipRole, MembershipStatus
from app.db.models.membership import WorkspaceMembership
from app.db.models.organization import Organization
from app.services.auth import bootstrap_tenant, resolve_principal


def test_invite_accept_joins_owner_workspace(session: Session) -> None:
    owner = AuthUser(user_id=f"owner_{uuid4().hex}", email="owner@example.com", claims={})
    owner_principal = bootstrap_tenant(session, user=owner)

    invite = WorkspaceMembership(
        workspace_id=owner_principal.workspace_id,
        organization_id=owner_principal.organization_id,
        supabase_user_id=f"invite:{uuid4()}",
        email="member@example.com",
        role=MembershipRole.MEMBER.value,
        status=MembershipStatus.INVITED.value,
    )
    session.add(invite)
    session.commit()

    member = AuthUser(user_id=f"member_{uuid4().hex}", email="member@example.com", claims={})
    principal = resolve_principal(session, user=member)

    assert principal.role == "member"
    assert principal.organization_id == owner_principal.organization_id
    assert principal.workspace_id == owner_principal.workspace_id
    assert len(list(session.exec(select(Organization)).all())) == 1

    row = session.get(WorkspaceMembership, principal.membership_id)
    assert row is not None
    assert row.status == MembershipStatus.ACTIVE.value
    assert row.supabase_user_id == member.user_id
