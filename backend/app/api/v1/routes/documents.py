"""Document upload, list, reprocess, and delete routes."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from app.api.deps import (
    PrincipalDep,
    RequestIdDep,
    SessionDep,
    SettingsDep,
    StorageClientDep,
    VectorStoreDep,
)
from app.core.exceptions import AppError
from app.services import documents as document_service
from app.services.ingestion_runner import run_ingestion_job
from app.services.parsing import SUPPORTED_EXTENSIONS

router = APIRouter(prefix="/documents", tags=["documents"])


class CreateDocumentRequest(BaseModel):
    filename: str
    size_bytes: int = Field(ge=0)
    mime_type: str | None = None
    title: str | None = None


class UploadCompleteRequest(BaseModel):
    storage_path: str
    checksum: str | None = None


@router.post("")
def create_document(
    body: CreateDocumentRequest,
    principal: PrincipalDep,
    session: SessionDep,
    settings: SettingsDep,
    storage: StorageClientDep,
    request_id: RequestIdDep,
) -> dict:
    suffix = Path(body.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise AppError(f"Unsupported file type: {suffix}", code="unsupported_type", status_code=422)
    doc = document_service.create_document(
        session,
        settings,
        principal=principal,
        title=body.title or body.filename,
        original_filename=body.filename,
        mime_type=body.mime_type or "application/octet-stream",
        size_bytes=body.size_bytes,
        request_id=request_id,
    )
    upload: dict[str, str] = {}
    if doc.storage_object_path:
        try:
            upload = storage.create_signed_upload(doc.storage_object_path)
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                f"Could not create signed upload URL: {exc}",
                code="signed_upload_failed",
                status_code=503,
            ) from exc

    return {
        "id": str(doc.id),
        "storage_path": doc.storage_object_path,
        "bucket": settings.supabase_storage_bucket,
        "status": doc.status,
        "upload_token": upload.get("token"),
        "upload_url": upload.get("signed_url"),
    }


@router.post("/{document_id}/upload-complete")
def upload_complete(
    document_id: UUID,
    body: UploadCompleteRequest,
    principal: PrincipalDep,
    session: SessionDep,
    settings: SettingsDep,
    storage: StorageClientDep,
    request_id: RequestIdDep,
    background_tasks: BackgroundTasks,
) -> dict:
    doc, job = document_service.complete_upload(
        session,
        settings,
        principal=principal,
        document_id=document_id,
        storage_object_path=body.storage_path,
        storage=storage,
        checksum=body.checksum,
        request_id=request_id,
    )
    background_tasks.add_task(run_ingestion_job, str(job.id))
    return {"document_id": str(doc.id), "job_id": str(job.id), "status": doc.status}


@router.get("")
def list_documents(principal: PrincipalDep, session: SessionDep) -> dict:
    rows = document_service.list_documents(session, principal=principal)
    return {
        "items": [
            {
                "id": str(d.id),
                "title": d.title,
                "filename": d.original_filename,
                "status": d.status,
                "size_bytes": d.size_bytes,
                "owner_user_id": d.owner_user_id,
                "storage_path": d.storage_object_path,
                "created_at": d.created_at.isoformat(),
                "error_message": d.error_message,
            }
            for d in rows
        ]
    }


@router.get("/{document_id}/view-url")
def view_document_url(
    document_id: UUID,
    principal: PrincipalDep,
    session: SessionDep,
    storage: StorageClientDep,
) -> dict:
    doc = document_service.get_document(session, principal=principal, document_id=document_id)
    if not doc.storage_object_path:
        raise AppError("Document has no uploaded file", code="no_storage_object", status_code=404)
    try:
        url = storage.create_signed_url(doc.storage_object_path, expires_in=3600)
    except Exception as exc:  # noqa: BLE001 — surface as 404 for missing objects
        raise AppError("Could not create view URL", code="signed_url_failed", status_code=404) from exc
    return {
        "document_id": str(doc.id),
        "url": url,
        "filename": doc.original_filename,
        "expires_in": 3600,
    }


@router.post("/{document_id}/reprocess")
def reprocess_document(
    document_id: UUID,
    principal: PrincipalDep,
    session: SessionDep,
    request_id: RequestIdDep,
    background_tasks: BackgroundTasks,
) -> dict:
    job = document_service.reprocess_document(
        session,
        principal=principal,
        document_id=document_id,
        request_id=request_id,
    )
    background_tasks.add_task(run_ingestion_job, str(job.id))
    return {
        "document_id": str(job.document_id),
        "job_id": str(job.id),
        "status": job.status,
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: UUID,
    principal: PrincipalDep,
    session: SessionDep,
    storage: StorageClientDep,
    vectors: VectorStoreDep,
    request_id: RequestIdDep,
) -> dict:
    doc = document_service.delete_document(
        session,
        principal=principal,
        document_id=document_id,
        storage=storage,
        vectors=vectors,
        request_id=request_id,
    )
    return {"id": str(doc.id), "status": doc.status}
