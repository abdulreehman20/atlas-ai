"""Stripe webhook idempotency ledger."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class StripeWebhookEvent(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "stripe_webhook_events"

    stripe_event_id: str = Field(max_length=128, unique=True, index=True)
    event_type: str = Field(max_length=128)
    status: str = Field(default="received", max_length=32)
    received_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
    processed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    error_message: str | None = Field(default=None, max_length=1024)
