"""Document lifecycle services."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.ai.vector_store import VectorStoreClient
from app.core.config import Settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import Principal
from app.db.models.document import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.document_version import DocumentVersion
from app.db.models.enums import DocumentStatus, IngestionJobStatus, UsageOperation
from app.db.models.ingestion_job import IngestionJob
from app.repositories import documents as document_repo
from app.repositories import usage as usage_repo
from app.services.audit import record_audit
from app.services.auth import require_role
from app.services.entitlements import assert_can_upload
from app.services.storage import StorageClient

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/html",
    "application/xhtml+xml",
    "application/octet-stream",
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

    assert_can_upload(
        session,
        settings,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        size_bytes=size_bytes,
    )

    doc_id = uuid4()
    storage_path = f"{principal.workspace_id}/{doc_id}/{original_filename}"
    document = Document(
        id=doc_id,
        workspace_id=principal.workspace_id,
        organization_id=principal.organization_id,
        owner_user_id=principal.user_id,
        title=title,
        original_filename=original_filename,
        mime_type=mime_type or "application/octet-stream",
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


def _verify_uploaded_object(
    storage: StorageClient,
    *,
    storage_object_path: str,
    expected_size_bytes: int | None,
    checksum: str | None,
) -> tuple[int, str]:
    if not storage.object_exists(storage_object_path):
        raise NotFoundError("Uploaded object not found in storage")
    content = storage.download(storage_object_path)
    actual_size = len(content)
    if (
        expected_size_bytes is not None
        and expected_size_bytes > 0
        and actual_size != expected_size_bytes
    ):
        raise ForbiddenError(
            f"Uploaded size mismatch: expected {expected_size_bytes}, got {actual_size}"
        )
    digest = hashlib.sha256(content).hexdigest()
    if checksum and checksum.lower() != digest.lower():
        raise ForbiddenError("Uploaded checksum mismatch")
    return actual_size, digest


def complete_upload(
    session: Session,
    settings: Settings,
    *,
    principal: Principal,
    document_id: UUID,
    storage_object_path: str,
    storage: StorageClient,
    checksum: str | None = None,
    request_id: str | None = None,
) -> tuple[Document, IngestionJob]:
    _ = settings
    document = document_repo.get_document(session, document_id=document_id)
    if document is None or document.workspace_id != principal.workspace_id:
        raise NotFoundError("Document not found")
    if document.owner_user_id != principal.user_id and principal.role != "owner":
        raise ForbiddenError("Not allowed")
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

    # Idempotent: already queued with a version — return latest job.
    if document.current_version_id is not None and document.status == DocumentStatus.QUEUED.value:
        existing_job = session.exec(
            select(IngestionJob)
            .where(IngestionJob.document_id == document.id)
            .order_by(IngestionJob.created_at.desc())  # type: ignore[arg-type]
        ).first()
        if existing_job is not None:
            return document, existing_job

    actual_size, digest = _verify_uploaded_object(
        storage,
        storage_object_path=storage_object_path,
        expected_size_bytes=document.size_bytes,
        checksum=checksum,
    )

    document.storage_object_path = storage_object_path
    document.checksum = digest
    document.size_bytes = actual_size
    document.status = DocumentStatus.UPLOADED.value

    version = DocumentVersion(
        document_id=document.id,
        workspace_id=document.workspace_id,
        version_number=1,
        storage_object_path=storage_object_path,
        checksum=digest,
        mime_type=document.mime_type,
        size_bytes=actual_size,
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
    storage: StorageClient,
    vectors: VectorStoreClient,
    request_id: str | None = None,
) -> Document:
    document = get_document(session, principal=principal, document_id=document_id)
    if principal.role != "owner" and document.owner_user_id != principal.user_id:
        raise ForbiddenError("Members may delete only their own uploads")

    document.status = DocumentStatus.DELETING.value
    session.add(document)
    session.commit()

    chunks = list(
        session.exec(
            select(DocumentChunk).where(DocumentChunk.document_id == document.id)
        ).all()
    )
    chunk_ids = [c.chunk_id for c in chunks]
    if chunk_ids:
        vectors.delete_ids(workspace_id=document.workspace_id, ids=chunk_ids)
    for chunk in chunks:
        session.delete(chunk)

    if document.storage_object_path:
        try:
            storage.delete(document.storage_object_path)
        except Exception:
            # Soft-delete still proceeds; storage orphan can be swept later.
            pass

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
    record_audit(
        session,
        action="document.reprocess",
        actor_user_id=principal.user_id,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        target_type="document",
        target_id=str(document.id),
        request_id=request_id,
    )
    session.commit()
    session.refresh(job)
    return job
