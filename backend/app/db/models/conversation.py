"""Chat conversation metadata."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "conversations"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    owner_user_id: str = Field(max_length=128, index=True)
    title: str = Field(default="New conversation", max_length=512)
    thread_id: str = Field(max_length=128, unique=True, index=True)
