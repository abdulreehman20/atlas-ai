"""Subscription entitlement state."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import PlanTier, SubscriptionStatus


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "subscriptions"

    organization_id: UUID = Field(foreign_key="organizations.id", unique=True, index=True)
    stripe_subscription_id: str | None = Field(default=None, max_length=128, unique=True)
    stripe_price_id: str | None = Field(default=None, max_length=128)
    status: str = Field(default=SubscriptionStatus.NONE.value, max_length=32)
    plan_tier: str = Field(default=PlanTier.FREE.value, max_length=32)
    current_period_start: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    current_period_end: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    cancel_at_period_end: bool = Field(default=False)
