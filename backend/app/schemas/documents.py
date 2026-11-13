"""Document API schemas."""

# DELETE -- This is not in use. Document routes define local Pydantic models instead.

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class DocumentCreateRequest(APIModel):
    title: str = Field(min_length=1, max_length=512)
    original_filename: str = Field(min_length=1, max_length=512)
    mime_type: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(ge=0)


class DocumentCreateResponse(APIModel):
    document_id: UUID
    status: str
    storage_object_path: str
    upload_bucket: str


class UploadCompleteRequest(APIModel):
    storage_object_path: str = Field(min_length=1, max_length=1024)
    checksum: str | None = Field(default=None, max_length=128)


class DocumentResponse(APIModel):
    id: UUID
    workspace_id: UUID
    title: str
    original_filename: str
    mime_type: str
    size_bytes: int
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(APIModel):
    items: list[DocumentResponse]
