"""Workspace entity — one per organization in v1."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import WorkspaceStatus


class Workspace(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "workspaces"

    organization_id: UUID = Field(foreign_key="organizations.id", index=True, unique=True)
    name: str = Field(max_length=255)
    slug: str = Field(max_length=255, index=True)
    status: str = Field(default=WorkspaceStatus.ACTIVE.value, max_length=32)
    system_prompt_override: str | None = Field(default=None)
