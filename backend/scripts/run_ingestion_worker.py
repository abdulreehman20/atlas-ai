"""Poll and process queued Atlas ingestion jobs.

Usage (from backend/):
  uv run python scripts/run_ingestion_worker.py
  uv run python scripts/run_ingestion_worker.py --once
  uv run python scripts/run_ingestion_worker.py --poll-interval 5
"""

from __future__ import annotations

import argparse
import signal
import time

from sqlmodel import Session

from app.ai.embeddings import BedrockEmbeddingClient, StubEmbeddingClient
from app.ai.vector_store import InMemoryVectorStore, PineconeVectorStore
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.db.engine import create_db_engine
from app.services.ingestion import process_next_queued_job
from app.services.storage import InMemoryStorageClient, SupabaseStorageClient

logger = get_logger(__name__)

_stop = False


def _handle_signal(signum: int, _frame: object) -> None:
    global _stop
    logger.info("Received signal %s; stopping after current job", signum)
    _stop = True


def _build_clients(settings: Settings):
    if settings.app_env == "test" or not settings.effective_supabase_key:
        storage = InMemoryStorageClient()
    else:
        storage = SupabaseStorageClient(settings)

    if settings.app_env == "test" or not settings.aws_access_key_id:
        embeddings = StubEmbeddingClient(dimension=settings.embedding_dimension)
    else:
        embeddings = BedrockEmbeddingClient(settings)

    if settings.app_env == "test" or not settings.pinecone_api_key:
        vectors = InMemoryVectorStore()
    else:
        vectors = PineconeVectorStore(settings)

    return storage, embeddings, vectors


def main() -> int:
    parser = argparse.ArgumentParser(description="Atlas ingestion worker loop")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one queued job then exit",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=3.0,
        help="Seconds to sleep when the queue is empty (default: 3)",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings)
    storage, embeddings, vectors = _build_clients(settings)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    logger.info(
        "Ingestion worker started once=%s poll_interval=%s env=%s",
        args.once,
        args.poll_interval,
        settings.app_env,
    )

    processed = 0
    while not _stop:
        with Session(engine) as session:
            job = process_next_queued_job(
                session,
                settings,
                storage=storage,
                embeddings=embeddings,
                vectors=vectors,
            )
        if job is None:
            if args.once:
                logger.info("No queued ingestion jobs")
                return 0
            time.sleep(args.poll_interval)
            continue

        processed += 1
        logger.info("Processed job %s status=%s", job.id, job.status)
        if args.once:
            return 0 if job.status == "succeeded" else 1

    logger.info("Ingestion worker stopped after %s job(s)", processed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
