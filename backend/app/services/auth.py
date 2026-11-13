"""Authentication bootstrap and principal resolution."""

from __future__ import annotations

import re
from uuid import UUID, uuid4

from sqlmodel import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import AuthUser, Principal, Role
from app.db.models.enums import MembershipRole, MembershipStatus, OrgStatus, WorkspaceStatus
from app.db.models.membership import WorkspaceMembership
from app.db.models.organization import Organization
from app.db.models.subscription import Subscription
from app.db.models.workspace import Workspace
from app.repositories import memberships as membership_repo
from app.services.audit import record_audit


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "workspace"


def bootstrap_tenant(
    session: Session,
    *,
    user: AuthUser,
    request_id: str | None = None,
) -> Principal:
    """Create org + workspace + owner membership on first authenticated access."""

    existing = membership_repo.get_active_membership(session, supabase_user_id=user.user_id)
    if existing is not None:
        return _to_principal(existing, email=user.email)

    org_name = (user.email.split("@")[0] if user.email else "Organization") + " Org"
    slug_base = _slugify(org_name)
    org = Organization(
        name=org_name, slug=f"{slug_base}-{uuid4().hex[:8]}", status=OrgStatus.ACTIVE.value
    )
    session.add(org)
    session.flush()

    workspace = Workspace(
        organization_id=org.id,
        name="Default Workspace",
        slug="default",
        status=WorkspaceStatus.ACTIVE.value,
    )
    session.add(workspace)
    session.flush()

    membership = WorkspaceMembership(
        workspace_id=workspace.id,
        organization_id=org.id,
        supabase_user_id=user.user_id,
        email=user.email,
        role=MembershipRole.OWNER.value,
        status=MembershipStatus.ACTIVE.value,
    )
    session.add(membership)
    session.add(Subscription(organization_id=org.id))

    record_audit(
        session,
        action="tenant.bootstrap",
        actor_user_id=user.user_id,
        organization_id=org.id,
        workspace_id=workspace.id,
        request_id=request_id,
    )
    session.commit()
    session.refresh(membership)
    return _to_principal(membership, email=user.email)


def resolve_principal(
    session: Session,
    *,
    user: AuthUser,
    request_id: str | None = None,
    bootstrap: bool = True,
) -> Principal:
    membership = membership_repo.get_active_membership(session, supabase_user_id=user.user_id)
    if membership is None:
        if not bootstrap:
            raise ForbiddenError("No workspace membership")
        return bootstrap_tenant(session, user=user, request_id=request_id)
    return _to_principal(membership, email=user.email)


def require_role(principal: Principal, *roles: Role) -> None:
    if principal.role not in roles:
        raise ForbiddenError("Insufficient role")


def _to_principal(membership: WorkspaceMembership, *, email: str | None) -> Principal:
    role: Role
    if membership.role == MembershipRole.OWNER.value:
        role = "owner"
    elif membership.role == MembershipRole.MEMBER.value:
        role = "member"
    else:
        raise UnauthorizedError("Invalid membership role")
    return Principal(
        user_id=membership.supabase_user_id,
        email=email or membership.email,
        organization_id=membership.organization_id,
        workspace_id=membership.workspace_id,
        role=role,
        membership_id=membership.id,
        membership_status=membership.status,
    )


def assert_workspace_access(principal: Principal, workspace_id: UUID) -> None:
    if principal.workspace_id != workspace_id:
        raise ForbiddenError("Workspace access denied")
