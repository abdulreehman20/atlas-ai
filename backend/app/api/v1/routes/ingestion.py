"""Ingestion job routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.api.deps import (
    EmbeddingClientDep,
    PrincipalDep,
    SessionDep,
    SettingsDep,
    StorageClientDep,
    VectorStoreDep,
)
from app.core.exceptions import NotFoundError
from app.db.models import IngestionJob
from app.services.auth import require_role
from app.services.ingestion import process_ingestion_job

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class IngestionJobResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: str
    attempt: int
    error_code: str | None = None
    error_message: str | None = None


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
def get_job(
    job_id: UUID,
    principal: PrincipalDep,
    session: SessionDep,
) -> IngestionJobResponse:
    job = session.get(IngestionJob, job_id)
    if job is None or job.workspace_id != principal.workspace_id:
        raise NotFoundError("Ingestion job not found")
    return IngestionJobResponse(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        attempt=job.attempt,
        error_code=job.error_code,
        error_message=job.error_message,
    )


@router.post("/jobs/{job_id}/run", response_model=IngestionJobResponse)
def run_job(
    job_id: UUID,
    principal: PrincipalDep,
    session: SessionDep,
    settings: SettingsDep,
    storage: StorageClientDep,
    embeddings: EmbeddingClientDep,
    vectors: VectorStoreDep,
    background_tasks: BackgroundTasks,
) -> IngestionJobResponse:
    require_role(principal, "owner")
    job = session.get(IngestionJob, job_id)
    if job is None or job.workspace_id != principal.workspace_id:
        raise NotFoundError("Ingestion job not found")

    # For API convenience in dev/test: process inline when app_env is test.
    if settings.app_env == "test":
        job = process_ingestion_job(
            session,
            settings,
            job_id=job_id,
            storage=storage,
            embeddings=embeddings,
            vectors=vectors,
        )
    else:
        background_tasks.add_task(
            process_ingestion_job,
            session,
            settings,
            job_id=job_id,
            storage=storage,
            embeddings=embeddings,
            vectors=vectors,
        )
    return IngestionJobResponse(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        attempt=job.attempt,
        error_code=job.error_code,
        error_message=job.error_message,
    )
