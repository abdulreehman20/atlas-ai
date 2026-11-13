"""Usage summary for owners."""

from __future__ import annotations

from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import PrincipalDep, SessionDep, SettingsDep
from app.db.models.enums import UsageOperation
from app.db.models.usage_record import UsageRecord
from app.repositories import documents as document_repo
from app.repositories import memberships as membership_repo
from app.repositories import usage as usage_repo
from app.services.auth import require_role
from app.services.entitlements import get_entitlements_for_org

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/summary")
def usage_summary(
    principal: PrincipalDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict:
    require_role(principal, "owner")

    entitlements = get_entitlements_for_org(
        session, settings, organization_id=principal.organization_id
    )
    chats = usage_repo.count_usage(
        session,
        organization_id=principal.organization_id,
        operation=UsageOperation.CHAT,
    )

    docs = document_repo.count_active_documents(session, workspace_id=principal.workspace_id)
    storage = document_repo.sum_storage_bytes(session, workspace_id=principal.workspace_id)
    members = membership_repo.count_active_members(session, workspace_id=principal.workspace_id)

    recent = session.exec(
        select(UsageRecord)
        .where(UsageRecord.organization_id == principal.organization_id)
        .order_by(UsageRecord.created_at.desc())
        .limit(20)
    ).all()

    return {
        "plan": entitlements.plan_tier.value,
        "usage": {
            "chats": chats,
            "documents": docs,
            "storage_bytes": storage,
            "members": members,
        },
        "limits": {
            "chats_monthly": entitlements.chat_monthly_limit,
            "documents": entitlements.document_limit,
            "storage_mib": entitlements.storage_mib,
            "members": entitlements.member_limit,
        },
        "recent": [
            {
                "id": str(r.id),
                "operation": r.operation,
                "created_at": r.created_at.isoformat(),
            }
            for r in recent
        ],
    }
