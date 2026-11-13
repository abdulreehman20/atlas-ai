"""Canonical extracted chunk text and provenance."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class DocumentChunk(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_version_id",
            "chunk_index",
            name="uq_document_version_chunk_index",
        ),
    )

    document_id: UUID = Field(foreign_key="documents.id", index=True)
    document_version_id: UUID = Field(foreign_key="document_versions.id", index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    chunk_id: str = Field(max_length=128, index=True)
    chunk_index: int = Field(ge=0)
    text: str = Field(sa_column=Column(Text, nullable=False))
    page_number: int | None = Field(default=None)
    section: str | None = Field(default=None, max_length=512)
    start_offset: int | None = Field(default=None)
    end_offset: int | None = Field(default=None)
    content_checksum: str | None = Field(default=None, max_length=128)
