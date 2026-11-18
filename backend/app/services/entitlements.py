"""Plan entitlements and limit enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, select

from app.core.config import Settings
from app.core.exceptions import EntitlementError
from app.db.models.enums import PlanTier, SubscriptionStatus, UsageOperation
from app.db.models.subscription import Subscription
from app.repositories import documents as document_repo
from app.repositories import memberships as membership_repo
from app.repositories import usage as usage_repo


@dataclass(frozen=True, slots=True)
class Entitlements:
    plan_tier: PlanTier
    member_limit: int
    document_limit: int
    max_file_size_mib: int
    storage_mib: int
    chat_monthly_limit: int
    custom_system_prompt: bool


def _is_pro(subscription: Subscription | None) -> bool:
    if subscription is None:
        return False
    if subscription.plan_tier != PlanTier.PRO.value:
        return False
    return subscription.status in {
        SubscriptionStatus.ACTIVE.value,
        SubscriptionStatus.TRIALING.value,
    }


def resolve_entitlements(
    settings: Settings,
    subscription: Subscription | None,
) -> Entitlements:
    if _is_pro(subscription):
        return Entitlements(
            plan_tier=PlanTier.PRO,
            member_limit=settings.pro_member_limit,
            document_limit=settings.pro_document_limit,
            max_file_size_mib=settings.pro_max_file_mib,
            storage_mib=settings.pro_storage_mib,
            chat_monthly_limit=settings.pro_chat_monthly,
            custom_system_prompt=True,
        )
    return Entitlements(
        plan_tier=PlanTier.FREE,
        member_limit=settings.free_member_limit,
        document_limit=settings.free_document_limit,
        max_file_size_mib=settings.free_max_file_mib,
        storage_mib=settings.free_storage_mib,
        chat_monthly_limit=settings.free_chat_monthly,
        custom_system_prompt=False,
    )


def get_organization_subscription(
    session: Session,
    *,
    organization_id: UUID,
) -> Subscription | None:
    statement = select(Subscription).where(Subscription.organization_id == organization_id)
    return session.exec(statement).first()


def get_entitlements_for_org(
    session: Session,
    settings: Settings,
    *,
    organization_id: UUID,
) -> Entitlements:
    subscription = get_organization_subscription(session, organization_id=organization_id)
    return resolve_entitlements(settings, subscription)


def assert_can_upload(
    session: Session,
    settings: Settings,
    *,
    organization_id: UUID,
    workspace_id: UUID,
    size_bytes: int,
) -> Entitlements:
    entitlements = get_entitlements_for_org(session, settings, organization_id=organization_id)
    max_bytes = entitlements.max_file_size_mib * 1024 * 1024

    if size_bytes > max_bytes:
        raise EntitlementError(
            f"File exceeds the Free plan limit of {entitlements.max_file_size_mib} MiB. Upgrade to Pro for larger uploads.",
            quota="max_file_size",
            details={
                "upgrade_required": True,
                "plan": "pro",
                "max_file_size_mib": entitlements.max_file_size_mib,
                "size_bytes": size_bytes,
            },
        )

    docs = document_repo.count_active_documents(session, workspace_id=workspace_id)
    if docs >= entitlements.document_limit:
        raise EntitlementError(
            f"Document limit reached ({entitlements.document_limit} on Free). Upgrade to Pro for more documents.",
            quota="documents",
            details={
                "upgrade_required": True,
                "plan": "pro",
                "document_limit": entitlements.document_limit,
                "documents_used": docs,
            },
        )

    used = document_repo.sum_storage_bytes(session, workspace_id=workspace_id)
    storage_cap = entitlements.storage_mib * 1024 * 1024
    if used + size_bytes > storage_cap:
        raise EntitlementError(
            f"Storage limit reached ({entitlements.storage_mib} MiB on Free). Upgrade to Pro for more storage.",
            quota="storage",
            details={
                "upgrade_required": True,
                "plan": "pro",
                "storage_mib": entitlements.storage_mib,
                "storage_used_bytes": used,
            },
        )
    return entitlements


def assert_can_chat(
    session: Session,
    settings: Settings,
    *,
    organization_id: UUID,
) -> Entitlements:
    entitlements = get_entitlements_for_org(session, settings, organization_id=organization_id)
    chats = usage_repo.count_usage(
        session,
        organization_id=organization_id,
        operation=UsageOperation.CHAT,
    )

    if chats >= entitlements.chat_monthly_limit:
        raise EntitlementError(
            f"Monthly chat limit reached ({entitlements.chat_monthly_limit} on Free). Upgrade to Pro for more chats.",
            quota="chats_monthly",
            details={
                "upgrade_required": True,
                "plan": "pro",
                "chat_monthly_limit": entitlements.chat_monthly_limit,
                "chats_used": chats,
            },
        )
    return entitlements


def assert_can_invite(
    session: Session,
    settings: Settings,
    *,
    organization_id: UUID,
    workspace_id: UUID,
) -> Entitlements:
    entitlements = get_entitlements_for_org(session, settings, organization_id=organization_id)
    members = membership_repo.count_seat_members(session, workspace_id=workspace_id)

    if members >= entitlements.member_limit:
        raise EntitlementError(
            "To invite more members, upgrade to the Pro plan.",
            quota="members",
            details={
                "upgrade_required": True,
                "plan": "pro",
                "member_limit": entitlements.member_limit,
                "members_used": members,
            },
        )
    return entitlements
