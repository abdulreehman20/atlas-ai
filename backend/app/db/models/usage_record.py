"""Plan and cost metering records."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import UsageOperation


class UsageRecord(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "usage_records"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    user_id: str | None = Field(default=None, max_length=128, index=True)
    operation: str = Field(default=UsageOperation.CHAT.value, max_length=64, index=True)
    units: int = Field(default=1, ge=0)
    model_id: str | None = Field(default=None, max_length=128)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    period_key: str = Field(max_length=32, index=True)
    request_id: str | None = Field(default=None, max_length=128)
