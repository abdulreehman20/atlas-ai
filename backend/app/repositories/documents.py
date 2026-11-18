"""Document repository helpers."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.db.models import Document
from app.db.models.document_chunk import DocumentChunk
from app.db.models.document_version import DocumentVersion
from app.db.models.enums import DocumentStatus
from app.db.models.ingestion_job import IngestionJob


def list_workspace_documents(session: Session, *, workspace_id: UUID) -> list[Document]:
    statement = (
        select(Document)
        .where(
            Document.workspace_id == workspace_id,
            Document.status != DocumentStatus.DELETED.value,
        )
        .order_by(Document.created_at.desc())
    )
    return list(session.exec(statement).all())


def get_document(session: Session, *, document_id: UUID) -> Document | None:
    return session.get(Document, document_id)


def count_active_documents(session: Session, *, workspace_id: UUID) -> int:
    statement = select(Document).where(
        Document.workspace_id == workspace_id,
        Document.status != DocumentStatus.DELETED.value,
    )
    return len(list(session.exec(statement).all()))


def sum_storage_bytes(session: Session, *, workspace_id: UUID) -> int:
    docs = list_workspace_documents(session, workspace_id=workspace_id)
    return sum(doc.size_bytes for doc in docs)


def get_chunks_by_ids(
    session: Session,
    *,
    workspace_id: UUID,
    chunk_ids: list[str],
) -> list[DocumentChunk]:
    if not chunk_ids:
        return []

    statement = select(DocumentChunk).where(
        DocumentChunk.workspace_id == workspace_id,
        DocumentChunk.chunk_id.in_(chunk_ids),  # type: ignore[attr-defined]
    )

    return list(session.exec(statement).all())


# DELETE -- This is not in use. No current callers.
def get_version(session: Session, *, version_id: UUID) -> DocumentVersion | None:
    return session.get(DocumentVersion, version_id)


# DELETE -- This is not in use. No current callers.
def get_job(session: Session, *, job_id: UUID) -> IngestionJob | None:
    return session.get(IngestionJob, job_id)
