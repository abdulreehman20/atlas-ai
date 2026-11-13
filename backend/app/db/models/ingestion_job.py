"""Durable ingestion job tracking."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime
from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import IngestionJobStatus


class IngestionJob(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "ingestion_jobs"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    document_id: UUID = Field(foreign_key="documents.id", index=True)
    document_version_id: UUID = Field(foreign_key="document_versions.id", index=True)
    status: str = Field(default=IngestionJobStatus.QUEUED.value, max_length=32, index=True)
    attempt: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=5, ge=1)
    lease_expires_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    next_retry_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=1024)
    correlation_id: str | None = Field(default=None, max_length=128)
