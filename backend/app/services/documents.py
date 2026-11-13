"""Document lifecycle services."""

# DELETE -- This is not in use. Routes reimplement document lifecycle inline
# in app/api/v1/routes/documents.py. Prefer wiring routes to this service later, or remove.

from __future__ import annotations

from uuid import UUID, uuid4

from sqlmodel import Session

from app.core.config import Settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import Principal
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.enums import DocumentStatus, IngestionJobStatus, UsageOperation
from app.db.models.ingestion_job import IngestionJob
from app.repositories import documents as document_repo
from app.repositories import usage as usage_repo
from app.services.audit import record_audit
from app.services.auth import require_role
from app.services.entitlements import assert_can_upload

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/html",
    "application/xhtml+xml",
}

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".html", ".htm"}


def _extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def create_document(
    session: Session,
    settings: Settings,
    *,
    principal: Principal,
    title: str,
    original_filename: str,
    mime_type: str,
    size_bytes: int,
    request_id: str | None = None,
) -> Document:
    ext = _extension(original_filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise ForbiddenError(f"Unsupported file extension: {ext or '(none)'}")
    if mime_type not in SUPPORTED_MIME_TYPES:
        raise ForbiddenError(f"Unsupported MIME type: {mime_type}")

    assert_can_upload(
        session,
        settings,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        size_bytes=size_bytes,
    )

    storage_path = f"{principal.workspace_id}/{uuid4()}/{original_filename}"
    document = Document(
        workspace_id=principal.workspace_id,
        organization_id=principal.organization_id,
        owner_user_id=principal.user_id,
        title=title,
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        storage_object_path=storage_path,
        status=DocumentStatus.UPLOAD_PENDING.value,
    )
    session.add(document)
    record_audit(
        session,
        action="document.create",
        actor_user_id=principal.user_id,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        target_type="document",
        target_id=str(document.id),
        request_id=request_id,
    )
    session.commit()
    session.refresh(document)
    return document


def complete_upload(
    session: Session,
    settings: Settings,
    *,
    principal: Principal,
    document_id: UUID,
    storage_object_path: str,
    checksum: str | None = None,
    request_id: str | None = None,
) -> tuple[Document, IngestionJob]:
    document = document_repo.get_document(session, document_id=document_id)
    if document is None or document.workspace_id != principal.workspace_id:
        raise NotFoundError("Document not found")
    if document.status not in {
        DocumentStatus.UPLOAD_PENDING.value,
        DocumentStatus.UPLOADED.value,
        DocumentStatus.QUEUED.value,
    }:
        raise ForbiddenError(f"Invalid document status for upload complete: {document.status}")

    if (
        document.storage_object_path
        and storage_object_path != document.storage_object_path
        and document.status == DocumentStatus.UPLOAD_PENDING.value
    ):
        raise ForbiddenError("Storage path mismatch")

    document.storage_object_path = storage_object_path
    document.checksum = checksum
    document.status = DocumentStatus.UPLOADED.value

    version = DocumentVersion(
        document_id=document.id,
        workspace_id=document.workspace_id,
        version_number=1,
        storage_object_path=storage_object_path,
        checksum=checksum,
        mime_type=document.mime_type,
        size_bytes=document.size_bytes,
        status=DocumentStatus.UPLOADED.value,
    )
    session.add(version)
    session.flush()
    document.current_version_id = version.id
    document.status = DocumentStatus.QUEUED.value

    job = IngestionJob(
        workspace_id=document.workspace_id,
        organization_id=document.organization_id,
        document_id=document.id,
        document_version_id=version.id,
        status=IngestionJobStatus.QUEUED.value,
        correlation_id=request_id,
    )
    session.add(job)
    usage_repo.add_usage(
        session,
        workspace_id=principal.workspace_id,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        operation=UsageOperation.UPLOAD,
        request_id=request_id,
    )
    record_audit(
        session,
        action="document.upload_complete",
        actor_user_id=principal.user_id,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        target_type="document",
        target_id=str(document.id),
        request_id=request_id,
    )
    session.commit()
    session.refresh(document)
    session.refresh(job)
    return document, job


def list_documents(session: Session, *, principal: Principal) -> list[Document]:
    return document_repo.list_workspace_documents(session, workspace_id=principal.workspace_id)


def get_document(session: Session, *, principal: Principal, document_id: UUID) -> Document:
    document = document_repo.get_document(session, document_id=document_id)
    if document is None or document.workspace_id != principal.workspace_id:
        raise NotFoundError("Document not found")
    return document


def delete_document(
    session: Session,
    *,
    principal: Principal,
    document_id: UUID,
    request_id: str | None = None,
) -> Document:
    document = get_document(session, principal=principal, document_id=document_id)
    if principal.role != "owner" and document.owner_user_id != principal.user_id:
        raise ForbiddenError("Members may delete only their own uploads")
    document.status = DocumentStatus.DELETED.value
    session.add(document)
    record_audit(
        session,
        action="document.delete",
        actor_user_id=principal.user_id,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        target_type="document",
        target_id=str(document.id),
        request_id=request_id,
    )
    session.commit()
    session.refresh(document)
    return document


def reprocess_document(
    session: Session,
    *,
    principal: Principal,
    document_id: UUID,
    request_id: str | None = None,
) -> IngestionJob:
    require_role(principal, "owner")
    document = get_document(session, principal=principal, document_id=document_id)
    if document.current_version_id is None or not document.storage_object_path:
        raise ForbiddenError("Document has no uploaded version to reprocess")
    document.status = DocumentStatus.QUEUED.value
    job = IngestionJob(
        workspace_id=document.workspace_id,
        organization_id=document.organization_id,
        document_id=document.id,
        document_version_id=document.current_version_id,
        status=IngestionJobStatus.QUEUED.value,
        correlation_id=request_id,
    )
    session.add(document)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job
