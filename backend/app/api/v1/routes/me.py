from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import PrincipalDep, SessionDep, SettingsDep
from app.db.models import Organization, Workspace, WorkspaceMembership
from app.services.entitlements import get_entitlements_for_org

router = APIRouter(tags=["me"])


@router.get("/me")
def me(principal: PrincipalDep, session: SessionDep, settings: SettingsDep) -> dict:
    org = session.get(Organization, principal.organization_id)
    ws = session.get(Workspace, principal.workspace_id)

    members = session.exec(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == principal.workspace_id,
            WorkspaceMembership.status == "active",
        )
    ).all()

    plan = get_entitlements_for_org(session, settings, organization_id=principal.organization_id)

    return {
        "user_id": principal.user_id,
        "email": principal.email,
        "role": principal.role,
        "organization": {"id": str(org.id), "name": org.name} if org else None,
        "workspace": {
            "id": str(ws.id),
            "name": ws.name,
            "system_prompt_override": (
                ws.system_prompt_override if principal.role == "owner" else None
            ),
        }
        if ws
        else None,
        "member_count": len(members),
        "plan": plan.plan_tier.value,
        "plan_tier": plan.plan_tier.value,
        "limits": {
            "members": plan.member_limit,
            "documents": plan.document_limit,
            "max_file_mib": plan.max_file_size_mib,
            "storage_mib": plan.storage_mib,
            "chats_monthly": plan.chat_monthly_limit,
            "custom_prompt": plan.custom_system_prompt,
        },
    }
