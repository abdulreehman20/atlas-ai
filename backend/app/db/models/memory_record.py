"""Approved long-term memory records."""

# DELETE -- This is not in use. Model/table exists but no app logic reads or writes it yet.

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Column, Text
from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class MemoryRecord(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "memory_records"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    user_id: str | None = Field(default=None, max_length=128, index=True)
    scope: str = Field(default="workspace", max_length=64)
    memory_type: str = Field(default="preference", max_length=64)
    content: str = Field(sa_column=Column(Text, nullable=False))
    provenance: str | None = Field(default=None, max_length=512)
    retention_days: int | None = Field(default=None)
    consent_granted: bool = Field(default=True)
    is_deleted: bool = Field(default=False)
