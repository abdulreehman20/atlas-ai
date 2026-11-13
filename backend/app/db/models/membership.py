"""Workspace membership entity."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.db.models.enums import MembershipRole, MembershipStatus


class WorkspaceMembership(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "supabase_user_id", name="uq_membership_workspace_user"),
    )

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    supabase_user_id: str = Field(max_length=128, index=True)
    email: str | None = Field(default=None, max_length=320)
    role: str = Field(default=MembershipRole.MEMBER.value, max_length=32)
    status: str = Field(default=MembershipStatus.ACTIVE.value, max_length=32)
    joined_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
    )
