"""Entitlement limit enforcement tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from app.core.config import Settings
from app.core.exceptions import EntitlementError
from app.core.security import Principal
from app.db.models.document import Document
from app.db.models.enums import DocumentStatus, PlanTier, SubscriptionStatus, UsageOperation
from app.db.models.subscription import Subscription
from app.db.models.usage_record import UsageRecord
from app.repositories.usage import current_period_key
from app.services.entitlements import assert_can_chat, assert_can_upload, resolve_entitlements


def test_free_vs_pro_limits() -> None:
    settings = Settings(app_env="test")
    free = resolve_entitlements(settings, None)
    assert free.plan_tier == PlanTier.FREE
    assert free.document_limit == settings.free_document_limit

    pro_sub = Subscription(
        organization_id=uuid4(),
        plan_tier=PlanTier.PRO.value,
        status=SubscriptionStatus.ACTIVE.value,
    )
    pro = resolve_entitlements(settings, pro_sub)
    assert pro.plan_tier == PlanTier.PRO
    assert pro.chat_monthly_limit == settings.pro_chat_monthly
    assert pro.custom_system_prompt is True


def test_upload_blocked_when_document_limit_reached(
    session: Session,
    principal: Principal,
) -> None:
    settings = Settings(
        app_env="test",
        free_document_limit=1,
        free_max_file_mib=10,
        free_storage_mib=500,
    )
    session.add(
        Document(
            workspace_id=principal.workspace_id,
            organization_id=principal.organization_id,
            owner_user_id=principal.user_id,
            title="Existing",
            original_filename="a.txt",
            mime_type="text/plain",
            size_bytes=10,
            status=DocumentStatus.READY.value,
        )
    )
    session.commit()

    with pytest.raises(EntitlementError) as exc:
        assert_can_upload(
            session,
            settings,
            organization_id=principal.organization_id,
            workspace_id=principal.workspace_id,
            size_bytes=100,
        )
    assert exc.value.code == "entitlement_exceeded"


def test_chat_blocked_when_monthly_limit_reached(
    session: Session,
    principal: Principal,
) -> None:
    settings = Settings(app_env="test", free_chat_monthly=2)
    for _ in range(2):
        session.add(
            UsageRecord(
                workspace_id=principal.workspace_id,
                organization_id=principal.organization_id,
                user_id=principal.user_id,
                operation=UsageOperation.CHAT.value,
                units=1,
                period_key=current_period_key(),
            )
        )
    session.commit()

    with pytest.raises(EntitlementError):
        assert_can_chat(
            session,
            settings,
            organization_id=principal.organization_id,
        )
