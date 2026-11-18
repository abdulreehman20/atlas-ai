"""Fire-and-forget ingestion runner for request BackgroundTasks."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from app.ai.embeddings import OpenRouterEmbeddingClient, StubEmbeddingClient
from app.ai.vector_store import InMemoryVectorStore, PineconeVectorStore
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.engine import create_db_engine
from app.services.ingestion import process_ingestion_job
from app.services.storage import InMemoryStorageClient, SupabaseStorageClient

logger = get_logger(__name__)


def run_ingestion_job(job_id: str) -> None:
    """Process one queued ingestion job in a fresh DB session."""

    settings = get_settings()
    engine = create_db_engine(settings)
    storage = (
        InMemoryStorageClient()
        if settings.app_env == "test" or not settings.effective_supabase_key
        else SupabaseStorageClient(settings)
    )
    embeddings = (
        StubEmbeddingClient(dimension=settings.embedding_dimension)
        if settings.app_env == "test" or not settings.openrouter_api_key
        else OpenRouterEmbeddingClient(settings)
    )
    vectors = (
        InMemoryVectorStore()
        if settings.app_env == "test" or not settings.pinecone_api_key
        else PineconeVectorStore(settings)
    )

    with Session(engine) as session:
        try:
            job = process_ingestion_job(
                session,
                settings,
                job_id=UUID(job_id),
                storage=storage,
                embeddings=embeddings,
                vectors=vectors,
            )
            logger.info(
                "background_ingestion_finished",
                extra={"job_id": job_id, "status": job.status},
            )
        except Exception:  # noqa: BLE001
            logger.exception("background_ingestion_failed", extra={"job_id": job_id})
