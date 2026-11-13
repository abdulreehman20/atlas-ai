"""Human-in-the-loop approval queue."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, Text
from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import ApprovalStatus


class Approval(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "approvals"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    requester_user_id: str = Field(max_length=128, index=True)
    reviewer_user_id: str | None = Field(default=None, max_length=128)
    action: str = Field(max_length=128)
    tool_name: str = Field(max_length=128)
    sanitized_arguments: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    summary: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(default=ApprovalStatus.PENDING.value, max_length=32, index=True)
    decision_note: str | None = Field(default=None, max_length=1024)
    checkpoint_thread_id: str | None = Field(default=None, max_length=128)
    decided_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    executed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
