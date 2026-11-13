"""Authorized retrieval over Pinecone + Postgres chunks."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, select

from app.ai.embeddings import EmbeddingClient
from app.ai.vector_store import VectorStoreClient
from app.db.models import Document
from app.db.models.enums import DocumentStatus
from app.repositories import documents as document_repo


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: str
    document_id: UUID
    document_version_id: UUID
    title: str
    text: str
    page_number: int | None
    section: str | None
    score: float


def retrieve(
    session: Session,
    *,
    workspace_id: UUID,
    query: str,
    top_k: int,
    embeddings: EmbeddingClient,
    vectors: VectorStoreClient,
) -> list[RetrievedChunk]:
    query_vector = embeddings.embed_query(query)
    matches = vectors.query(workspace_id=workspace_id, vector=query_vector, top_k=top_k)
    if not matches:
        return []

    chunk_ids = [match.id for match in matches]
    score_by_id = {match.id: match.score for match in matches}
    db_chunks = document_repo.get_chunks_by_ids(
        session, workspace_id=workspace_id, chunk_ids=chunk_ids
    )
    if not db_chunks:
        return []

    document_ids = {chunk.document_id for chunk in db_chunks}
    docs = {
        doc.id: doc
        for doc in session.exec(
            select(Document).where(
                Document.workspace_id == workspace_id,
                Document.id.in_(list(document_ids)),  # type: ignore[attr-defined]
                Document.status == DocumentStatus.READY.value,
            )
        ).all()
    }

    results: list[RetrievedChunk] = []
    for chunk in db_chunks:
        document = docs.get(chunk.document_id)
        if document is None:
            continue
        results.append(
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_version_id=chunk.document_version_id,
                title=document.title,
                text=chunk.text,
                page_number=chunk.page_number,
                section=chunk.section,
                score=score_by_id.get(chunk.chunk_id, 0.0),
            )
        )
    results.sort(key=lambda item: item.score, reverse=True)
    return results
