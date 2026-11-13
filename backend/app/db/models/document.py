"""Document metadata entity."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import DocumentStatus


class Document(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "documents"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    owner_user_id: str = Field(max_length=128, index=True)
    title: str = Field(max_length=512)
    original_filename: str = Field(max_length=512)
    mime_type: str = Field(max_length=128)
    size_bytes: int = Field(default=0, ge=0)
    checksum: str | None = Field(default=None, max_length=128)
    storage_object_path: str | None = Field(default=None, max_length=1024)
    status: str = Field(default=DocumentStatus.UPLOAD_PENDING.value, max_length=32)
    current_version_id: UUID | None = Field(default=None, index=True)
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=1024)
