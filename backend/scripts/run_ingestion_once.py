"""Claim and process one queued ingestion job.

Usage:
  uv run python scripts/run_ingestion_once.py
  uv run python scripts/run_ingestion_once.py --job-id <uuid>
"""

from __future__ import annotations

import argparse
from uuid import UUID

from sqlmodel import Session

from app.ai.embeddings import OpenRouterEmbeddingClient, StubEmbeddingClient
from app.ai.vector_store import InMemoryVectorStore, PineconeVectorStore
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.engine import create_db_engine
from app.services.ingestion import process_ingestion_job, process_next_queued_job
from app.services.storage import InMemoryStorageClient, SupabaseStorageClient

logger = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Process one Atlas ingestion job")
    parser.add_argument("--job-id", type=str, default=None)
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings)

    if settings.effective_supabase_key and settings.supabase_url:
        storage = SupabaseStorageClient(settings)
    else:
        storage = InMemoryStorageClient()

    if settings.openrouter_api_key:
        embeddings = OpenRouterEmbeddingClient(settings)
    else:
        embeddings = StubEmbeddingClient(dimension=settings.embedding_dimension)

    if settings.pinecone_api_key:
        vectors = PineconeVectorStore(settings)
    else:
        vectors = InMemoryVectorStore()

    with Session(engine) as session:
        if args.job_id:
            job = process_ingestion_job(
                session,
                settings,
                job_id=UUID(args.job_id),
                storage=storage,
                embeddings=embeddings,
                vectors=vectors,
            )
        else:
            job = process_next_queued_job(
                session,
                settings,
                storage=storage,
                embeddings=embeddings,
                vectors=vectors,
            )
        if job is None:
            logger.info("No queued ingestion jobs")
            return 0
        logger.info("Processed job %s status=%s", job.id, job.status)
        return 0 if job.status == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
