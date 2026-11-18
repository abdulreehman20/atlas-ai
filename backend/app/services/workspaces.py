"""Workspace settings services."""

# DELETE -- This is not in use. Routes reimplement workspace/prompt logic inline
# in app/api/v1/routes/workspaces.py. Prefer wiring routes to this service later, or remove.

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from app.core.config import Settings
from app.core.exceptions import EntitlementError, NotFoundError
from app.core.security import Principal
from app.db.models.organization import Organization
from app.db.models.workspace import Workspace
from app.services.auth import require_role
from app.services.entitlements import get_entitlements_for_org


def get_organization(session: Session, *, organization_id: UUID) -> Organization:
    org = session.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("Organization not found")
    return org


def update_system_prompt(
    session: Session,
    settings: Settings,
    *,
    principal: Principal,
    system_prompt_override: str | None,
) -> Workspace:
    require_role(principal, "owner")
    entitlements = get_entitlements_for_org(
        session, settings, organization_id=principal.organization_id
    )
    if system_prompt_override and not entitlements.custom_system_prompt:
        raise EntitlementError(
            "Custom system prompt requires the Pro plan. Upgrade to Pro to save workspace prompt overrides.",
            quota="custom_system_prompt",
            details={"upgrade_required": True, "plan": "pro"},
        )
    workspace = session.get(Workspace, principal.workspace_id)
    if workspace is None:
        raise NotFoundError("Workspace not found")
    workspace.system_prompt_override = system_prompt_override
    session.add(workspace)
    session.commit()
    session.refresh(workspace)
    return workspace


def load_org_by_workspace(session: Session, *, workspace_id: UUID) -> Organization | None:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        return None
    return session.get(Organization, workspace.organization_id)
