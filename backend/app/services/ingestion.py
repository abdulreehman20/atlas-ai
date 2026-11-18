"""Durable document ingestion pipeline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlmodel import Session, select

from app.ai.chunking import CHUNKER_VERSION, chunk_document
from app.ai.embeddings import EmbeddingClient
from app.ai.parsing import PARSER_VERSION, parse_bytes
from app.ai.vector_store import VectorStoreClient
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.models import Document, DocumentChunk, DocumentVersion, IngestionJob
from app.db.models.enums import DocumentStatus, IngestionJobStatus
from app.services.storage import StorageClient

logger = get_logger(__name__)


def claim_job(session: Session, *, job_id: UUID, lease_seconds: int = 300) -> IngestionJob | None:
    job = session.get(IngestionJob, job_id)
    if job is None:
        return None
    if job.status not in {IngestionJobStatus.QUEUED.value, IngestionJobStatus.FAILED.value}:
        if job.status == IngestionJobStatus.RUNNING.value:
            if job.lease_expires_at and job.lease_expires_at > datetime.now(UTC):
                return None
        else:
            return None
    job.status = IngestionJobStatus.RUNNING.value
    job.attempt += 1
    job.lease_expires_at = datetime.now(UTC) + timedelta(seconds=lease_seconds)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def process_ingestion_job(
    session: Session,
    settings: Settings,
    *,
    job_id: UUID,
    storage: StorageClient,
    embeddings: EmbeddingClient,
    vectors: VectorStoreClient,
) -> IngestionJob:
    job = claim_job(session, job_id=job_id)
    if job is None:
        existing = session.get(IngestionJob, job_id)
        if existing is None:
            raise NotFoundError("Ingestion job not found")
        return existing

    document = session.get(Document, job.document_id)
    version = session.get(DocumentVersion, job.document_version_id)
    if document is None or version is None:
        return _fail(session, job, document, "missing_document", "Document or version missing")

    document.status = DocumentStatus.PROCESSING.value
    version.status = DocumentStatus.PROCESSING.value
    session.add(document)
    session.add(version)
    session.commit()

    try:
        content = storage.download(version.storage_object_path)
        parsed = parse_bytes(
            content=content,
            mime_type=version.mime_type,
            filename=document.original_filename,
        )
        chunks = chunk_document(
            parsed,
            document_version_id=version.id,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        if not chunks:
            raise ValueError("No chunks produced")

        # Replace prior chunks for this version (idempotent reprocess).
        prior = session.exec(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version.id)
        ).all()
        prior_ids = [chunk.chunk_id for chunk in prior]
        for chunk in prior:
            session.delete(chunk)
        if prior_ids:
            vectors.delete_ids(workspace_id=job.workspace_id, ids=prior_ids)

        texts = [chunk.text.replace("\x00", "") for chunk in chunks]
        embeddings_list = embeddings.embed_documents(texts)
        upsert_payload = []
        for chunk, values, clean_text in zip(chunks, embeddings_list, texts, strict=True):
            session.add(
                DocumentChunk(
                    document_id=document.id,
                    document_version_id=version.id,
                    workspace_id=job.workspace_id,
                    chunk_id=chunk.chunk_id,
                    chunk_index=chunk.chunk_index,
                    text=clean_text,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    start_offset=chunk.start_offset,
                    end_offset=chunk.end_offset,
                    content_checksum=chunk.content_checksum,
                )
            )
            upsert_payload.append(
                (
                    chunk.chunk_id,
                    values,
                    {
                        "document_id": str(document.id),
                        "document_version_id": str(version.id),
                        "workspace_id": str(job.workspace_id),
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                    },
                )
            )
        vectors.upsert(workspace_id=job.workspace_id, vectors=upsert_payload)

        version.parser_version = PARSER_VERSION
        version.chunker_version = CHUNKER_VERSION
        version.embedding_model_id = settings.openrouter_embedding_model
        version.status = DocumentStatus.READY.value
        document.status = DocumentStatus.READY.value
        document.error_code = None
        document.error_message = None
        job.status = IngestionJobStatus.SUCCEEDED.value
        job.error_code = None
        job.error_message = None
        session.add(version)
        session.add(document)
        session.add(job)
        session.commit()
        session.refresh(job)
        return job
    except Exception as exc:  # noqa: BLE001 — sanitize into job failure
        logger.exception("Ingestion failed job_id=%s", job_id)
        return _fail(session, job, document, "ingestion_failed", str(exc)[:1000])


def _fail(
    session: Session,
    job: IngestionJob,
    document: Document | None,
    code: str,
    message: str,
) -> IngestionJob:
    # Prior flush may have aborted the transaction (e.g. Postgres NUL rejection).
    session.rollback()
    job = session.get(IngestionJob, job.id) or job
    if document is not None and getattr(document, "id", None) is not None:
        document = session.get(Document, document.id) or document
    job.status = IngestionJobStatus.FAILED.value
    job.error_code = code
    job.error_message = message
    if document is not None:
        document.status = DocumentStatus.FAILED.value
        document.error_code = code
        document.error_message = message
        session.add(document)
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def process_next_queued_job(
    session: Session,
    settings: Settings,
    *,
    storage: StorageClient,
    embeddings: EmbeddingClient,
    vectors: VectorStoreClient,
) -> IngestionJob | None:
    now = datetime.now(UTC)
    queued = session.exec(
        select(IngestionJob)
        .where(IngestionJob.status == IngestionJobStatus.QUEUED.value)
        .order_by(IngestionJob.created_at.asc())
    ).first()
    if queued is not None:
        return process_ingestion_job(
            session,
            settings,
            job_id=queued.id,
            storage=storage,
            embeddings=embeddings,
            vectors=vectors,
        )

    # Reclaim jobs left RUNNING after a crashed BackgroundTask / worker.
    stale = session.exec(
        select(IngestionJob)
        .where(
            IngestionJob.status == IngestionJobStatus.RUNNING.value,
            IngestionJob.lease_expires_at.is_not(None),
            IngestionJob.lease_expires_at < now,
        )
        .order_by(IngestionJob.created_at.asc())
    ).first()
    if stale is None:
        return None
    return process_ingestion_job(
        session,
        settings,
        job_id=stale.id,
        storage=storage,
        embeddings=embeddings,
        vectors=vectors,
    )
