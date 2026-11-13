"""Security and business audit events."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class AuditEvent(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "audit_events"

    actor_user_id: str | None = Field(default=None, max_length=128, index=True)
    organization_id: UUID | None = Field(default=None, foreign_key="organizations.id", index=True)
    workspace_id: UUID | None = Field(default=None, foreign_key="workspaces.id", index=True)
    action: str = Field(max_length=128, index=True)
    target_type: str | None = Field(default=None, max_length=64)
    target_id: str | None = Field(default=None, max_length=128)
    metadata_json: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    request_id: str | None = Field(default=None, max_length=128)
    trace_id: str | None = Field(default=None, max_length=128)
