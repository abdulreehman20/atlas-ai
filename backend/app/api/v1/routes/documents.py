from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlmodel import col, select

from app.api.deps import PrincipalDep, SessionDep, SettingsDep
from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.db.models import Document, DocumentVersion, IngestionJob
from app.db.models.enums import DocumentStatus, IngestionJobStatus
from app.services.entitlements import assert_can_upload
from app.services.parsing import SUPPORTED_EXTENSIONS

router = APIRouter(prefix="/documents", tags=["documents"])


class CreateDocumentRequest(BaseModel):
    filename: str
    size_bytes: int = Field(ge=0)
    mime_type: str | None = None
    title: str | None = None


class UploadCompleteRequest(BaseModel):
    storage_path: str


@router.post("")
def create_document(
    body: CreateDocumentRequest,
    principal: PrincipalDep,
    session: SessionDep,
    settings: SettingsDep,
) -> dict:
    suffix = Path(body.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise AppError(f"Unsupported file type: {suffix}", code="unsupported_type", status_code=422)
    assert_can_upload(
        session,
        settings,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        size_bytes=body.size_bytes,
    )
    doc_id = uuid4()
    storage_path = f"{principal.workspace_id}/{doc_id}/{body.filename}"
    doc = Document(
        id=doc_id,
        workspace_id=principal.workspace_id,
        organization_id=principal.organization_id,
        owner_user_id=principal.user_id,
        title=body.title or body.filename,
        original_filename=body.filename,
        storage_object_path=storage_path,
        mime_type=body.mime_type or "application/octet-stream",
        size_bytes=body.size_bytes,
        status=DocumentStatus.UPLOAD_PENDING.value,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return {
        "id": str(doc.id),
        "storage_path": storage_path,
        "bucket": settings.supabase_storage_bucket,
        "status": doc.status,
    }


@router.post("/{document_id}/upload-complete")
def upload_complete(
    document_id: UUID,
    body: UploadCompleteRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> dict:
    doc = session.get(Document, document_id)
    if doc is None or doc.workspace_id != principal.workspace_id:
        raise NotFoundError("Document not found")
    if doc.owner_user_id != principal.user_id and principal.role != "owner":
        raise ForbiddenError("Not allowed")
    doc.storage_object_path = body.storage_path
    doc.status = DocumentStatus.UPLOADED.value
    version = DocumentVersion(
        document_id=doc.id,
        workspace_id=doc.workspace_id,
        version_number=1,
        storage_object_path=body.storage_path,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        status=DocumentStatus.UPLOADED.value,
    )
    session.add(doc)
    session.add(version)
    session.flush()
    doc.current_version_id = version.id
    job = IngestionJob(
        document_id=doc.id,
        document_version_id=version.id,
        workspace_id=doc.workspace_id,
        organization_id=doc.organization_id,
        status=IngestionJobStatus.QUEUED.value,
    )
    doc.status = DocumentStatus.QUEUED.value
    session.add(job)
    session.add(doc)
    session.commit()
    session.refresh(job)
    return {"document_id": str(doc.id), "job_id": str(job.id), "status": doc.status}


@router.get("")
def list_documents(principal: PrincipalDep, session: SessionDep) -> dict:
    rows = session.exec(
        select(Document)
        .where(
            Document.workspace_id == principal.workspace_id,
            col(Document.status) != DocumentStatus.DELETED.value,
        )
        .order_by(col(Document.created_at).desc())
    ).all()
    return {
        "items": [
            {
                "id": str(d.id),
                "title": d.title,
                "filename": d.original_filename,
                "status": d.status,
                "size_bytes": d.size_bytes,
                "owner_user_id": d.owner_user_id,
                "created_at": d.created_at.isoformat(),
            }
            for d in rows
        ]
    }


@router.delete("/{document_id}")
def delete_document(document_id: UUID, principal: PrincipalDep, session: SessionDep) -> dict:
    doc = session.get(Document, document_id)
    if doc is None or doc.workspace_id != principal.workspace_id:
        raise NotFoundError("Document not found")
    if principal.role != "owner" and doc.owner_user_id != principal.user_id:
        raise ForbiddenError("Members may delete only their own documents")
    doc.status = DocumentStatus.DELETED.value
    session.add(doc)
    session.commit()
    return {"id": str(doc.id), "status": "deleted"}
