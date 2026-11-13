"""Workspace settings and member management."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlmodel import select

from app.api.deps import PrincipalDep, SessionDep, SettingsDep
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import Principal
from app.db.models.enums import MembershipRole, MembershipStatus
from app.db.models.membership import WorkspaceMembership
from app.db.models.workspace import Workspace
from app.services.auth import require_role
from app.services.entitlements import assert_can_invite, get_entitlements_for_org

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# NOTE: Duplicate of billing.require_owner/OwnerDep — consolidate into app.api.deps later.
def require_owner(principal: PrincipalDep) -> Principal:
    require_role(principal, "owner")
    return principal


OwnerDep = Annotated[Principal, Depends(require_owner)]


class PromptUpdate(BaseModel):
    system_prompt_override: str | None = None


class InviteRequest(BaseModel):
    email: EmailStr


@router.get("/current")
def get_current_workspace(principal: PrincipalDep, session: SessionDep) -> dict:
    ws = session.get(Workspace, principal.workspace_id)
    if ws is None:
        raise NotFoundError("Workspace not found")
    return {
        "organization_id": str(principal.organization_id),
        "workspace_id": str(principal.workspace_id),
        "system_prompt_override": ws.system_prompt_override,
    }


@router.put("/current/system-prompt")
def put_system_prompt(
    body: PromptUpdate,
    principal: OwnerDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict:
    entitlements = get_entitlements_for_org(
        session, settings, organization_id=principal.organization_id
    )
    if body.system_prompt_override and not entitlements.custom_system_prompt:
        raise ForbiddenError("Custom system prompt requires Pro plan")

    ws = session.get(Workspace, principal.workspace_id)
    if ws is None:
        raise NotFoundError("Workspace not found")

    ws.system_prompt_override = body.system_prompt_override
    session.add(ws)
    session.commit()
    session.refresh(ws)

    return {
        "organization_id": str(principal.organization_id),
        "workspace_id": str(ws.id),
        "system_prompt_override": ws.system_prompt_override,
    }


@router.get("/current/members")
def list_members(principal: PrincipalDep, session: SessionDep) -> dict:
    rows = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == principal.workspace_id,
            WorkspaceMembership.status != MembershipStatus.REMOVED.value,
        )
    ).all()
    return {
        "items": [
            {
                "id": str(m.id),
                "user_id": m.supabase_user_id,
                "email": m.email,
                "role": m.role,
                "status": m.status,
            }
            for m in rows
        ]
    }


@router.post("/current/members")
def invite_member(
    body: InviteRequest,
    principal: OwnerDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict:
    assert_can_invite(
        session,
        settings,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
    )

    email = body.email.lower()
    existing = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == principal.workspace_id,
            WorkspaceMembership.email == email,
            WorkspaceMembership.status != MembershipStatus.REMOVED.value,
        )
    ).first()
    if existing:
        raise ConflictError("Member already exists")

    membership = WorkspaceMembership(
        workspace_id=principal.workspace_id,
        organization_id=principal.organization_id,
        supabase_user_id=f"invite:{uuid4()}",
        email=email,
        role=MembershipRole.MEMBER.value,
        status=MembershipStatus.INVITED.value,
    )
    session.add(membership)
    session.commit()
    session.refresh(membership)

    return {
        "id": str(membership.id),
        "user_id": membership.supabase_user_id,
        "email": membership.email,
        "role": membership.role,
        "status": membership.status,
    }


@router.delete("/current/members/{membership_id}")
def remove_member(membership_id: UUID, principal: OwnerDep, session: SessionDep) -> dict:

    row = session.get(WorkspaceMembership, membership_id)

    if row is None or row.workspace_id != principal.workspace_id:
        raise NotFoundError("Membership not found")

    if row.role == MembershipRole.OWNER.value:
        raise AppError("Cannot remove the owner", code="cannot_remove_owner", status_code=400)

    row.status = MembershipStatus.REMOVED.value
    session.add(row)
    session.commit()
    return {"id": str(row.id), "status": "removed"}
