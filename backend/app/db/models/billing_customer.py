"""Stripe customer mapping per organization."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class BillingCustomer(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "billing_customers"

    organization_id: UUID = Field(foreign_key="organizations.id", unique=True, index=True)
    stripe_customer_id: str = Field(max_length=128, unique=True, index=True)
    billing_email: str | None = Field(default=None, max_length=320)
