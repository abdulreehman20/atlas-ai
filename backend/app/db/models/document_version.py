"""Immutable document version entity."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import DocumentStatus


class DocumentVersion(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_document_version_number"),
    )

    document_id: UUID = Field(foreign_key="documents.id", index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    version_number: int = Field(ge=1)
    storage_object_path: str = Field(max_length=1024)
    checksum: str | None = Field(default=None, max_length=128)
    mime_type: str = Field(max_length=128)
    size_bytes: int = Field(default=0, ge=0)
    parser_version: str | None = Field(default=None, max_length=64)
    chunker_version: str | None = Field(default=None, max_length=64)
    embedding_model_id: str | None = Field(default=None, max_length=128)
    status: str = Field(default=DocumentStatus.UPLOADED.value, max_length=32)
