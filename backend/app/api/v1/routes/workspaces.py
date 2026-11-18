"""Workspace settings and member management."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import select

from app.api.deps import PrincipalDep, SessionDep, SettingsDep
from app.core.exceptions import (
    AppError,
    ConflictError,
    EntitlementError,
    NotFoundError,
)
from app.core.security import Principal
from app.db.models.document import Document
from app.db.models.enums import (
    DocumentStatus,
    MembershipRole,
    MembershipStatus,
    OrgStatus,
    PlanTier,
    WorkspaceStatus,
)
from app.db.models.membership import WorkspaceMembership
from app.db.models.organization import Organization
from app.db.models.workspace import Workspace
from app.ai.prompts import LOCKED_SYSTEM_PROMPT
from app.services import supabase_auth
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


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    system_prompt_override: str | None = None


class InviteRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)


@router.get("/current")
def get_current_workspace(principal: PrincipalDep, session: SessionDep) -> dict:
    ws = session.get(Workspace, principal.workspace_id)
    if ws is None:
        raise NotFoundError("Workspace not found")
    return {
        "organization_id": str(principal.organization_id),
        "workspace_id": str(principal.workspace_id),
        "name": ws.name,
        "slug": ws.slug,
        "status": ws.status,
        "system_prompt_override": ws.system_prompt_override,
        "default_system_prompt": LOCKED_SYSTEM_PROMPT,
        "effective_system_prompt": ws.system_prompt_override or LOCKED_SYSTEM_PROMPT,
    }


@router.put("/current")
def update_current_workspace(
    body: WorkspaceUpdate,
    principal: OwnerDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict:
    ws = session.get(Workspace, principal.workspace_id)
    if ws is None:
        raise NotFoundError("Workspace not found")

    if body.system_prompt_override is not None:
        entitlements = get_entitlements_for_org(
            session, settings, organization_id=principal.organization_id
        )
        if body.system_prompt_override and not entitlements.custom_system_prompt:
            raise EntitlementError(
                "Custom system prompt requires the Pro plan. Upgrade to Pro to save workspace prompt overrides.",
                quota="custom_system_prompt",
                details={"upgrade_required": True, "plan": "pro"},
            )
        ws.system_prompt_override = body.system_prompt_override

    if body.name is not None:
        ws.name = body.name.strip()
        if not ws.name:
            raise AppError("Workspace name is required", code="invalid_name", status_code=422)

    session.add(ws)
    session.commit()
    session.refresh(ws)

    return {
        "organization_id": str(principal.organization_id),
        "workspace_id": str(ws.id),
        "name": ws.name,
        "slug": ws.slug,
        "status": ws.status,
        "system_prompt_override": ws.system_prompt_override,
        "default_system_prompt": LOCKED_SYSTEM_PROMPT,
        "effective_system_prompt": ws.system_prompt_override or LOCKED_SYSTEM_PROMPT,
    }


@router.put("/current/system-prompt")
def put_system_prompt(
    body: PromptUpdate,
    principal: OwnerDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict:
    return update_current_workspace(
        WorkspaceUpdate(system_prompt_override=body.system_prompt_override),
        principal,
        session,
        settings,
    )


@router.delete("/current")
def delete_current_workspace(principal: OwnerDep, session: SessionDep) -> dict:
    """Archive the workspace and related tenant data (owner-only)."""

    ws = session.get(Workspace, principal.workspace_id)
    if ws is None:
        raise NotFoundError("Workspace not found")
    org = session.get(Organization, principal.organization_id)

    memberships = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == principal.workspace_id
        )
    ).all()
    for row in memberships:
        row.status = MembershipStatus.REMOVED.value
        session.add(row)

    documents = session.exec(
        select(Document).where(Document.workspace_id == principal.workspace_id)
    ).all()
    for doc in documents:
        if doc.status != DocumentStatus.DELETED.value:
            doc.status = DocumentStatus.DELETED.value
            session.add(doc)

    ws.status = WorkspaceStatus.ARCHIVED.value
    session.add(ws)
    if org is not None:
        org.status = OrgStatus.SUSPENDED.value
        session.add(org)

    session.commit()
    return {
        "workspace_id": str(ws.id),
        "organization_id": str(principal.organization_id),
        "status": ws.status,
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

    first_name = body.first_name.strip()
    last_name = body.last_name.strip()
    metadata = {
        "first_name": first_name,
        "last_name": last_name,
        "full_name": " ".join(part for part in (first_name, last_name) if part).strip(),
        "invited_to_workspace_id": str(principal.workspace_id),
    }

    # Client page can read invite tokens from the URL hash and collect a password.
    redirect_to = f"{settings.frontend_url.rstrip('/')}/auth/accept-invite"
    email_sent = False
    invited_user_id = f"invite:{uuid4()}"
    try:
        invited = supabase_auth.invite_user_by_email(
            settings,
            email=email,
            redirect_to=redirect_to,
            data=metadata,
        )
        email_sent = bool(invited.get("email_sent"))
        if invited.get("id"):
            invited_user_id = str(invited["id"])
    except AppError as exc:
        # User already registered — keep membership invite; they can sign in to accept.
        details = exc.details if isinstance(exc.details, dict) else {}
        message = str(exc.message if hasattr(exc, "message") else exc).lower()
        already_exists = exc.status_code in {422, 400} and (
            "already" in message or details.get("error_code") == "email_exists"
        )
        if already_exists:
            pass
        elif "rate limit" in message or details.get("error_code") in {
            "over_email_send_rate_limit",
            "email_rate_limit_exceeded",
        }:
            entitlements = get_entitlements_for_org(
                session,
                settings,
                organization_id=principal.organization_id,
            )
            if entitlements.plan_tier == PlanTier.FREE:
                raise EntitlementError(
                    "To invite more members, upgrade to the Pro plan.",
                    quota="members",
                    details={"upgrade_required": True, "plan": "pro"},
                ) from exc
            raise AppError(
                "Invite email rate limit reached. Please try again in a few minutes.",
                code="invite_rate_limited",
                status_code=429,
            ) from exc
        else:
            raise

    membership = WorkspaceMembership(
        workspace_id=principal.workspace_id,
        organization_id=principal.organization_id,
        supabase_user_id=invited_user_id,
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
        "email_sent": email_sent,
        "first_name": first_name,
        "last_name": last_name,
    }


@router.post("/current/members/accept")
def accept_invite(principal: PrincipalDep) -> dict:
    """Confirm invite acceptance.

    Acceptance also runs implicitly inside principal resolution on first
    authenticated request (`/me`, etc.) when an INVITED row matches the email.
    """

    return {
        "id": str(principal.membership_id),
        "user_id": principal.user_id,
        "email": principal.email,
        "role": principal.role,
        "status": principal.membership_status,
        "accepted": principal.role == "member",
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
