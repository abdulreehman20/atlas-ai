"""Long-term memory record routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import PrincipalDep, RequestIdDep, SessionDep
from app.services import memory_records as memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    memory_type: str = Field(default="preference", max_length=64)
    scope: str = Field(default="user", max_length=32)
    retention_days: int | None = Field(default=None, ge=1)


@router.get("")
def list_memories(principal: PrincipalDep, session: SessionDep) -> dict:
    rows = memory_service.list_memories(session, principal=principal)
    return {
        "items": [
            {
                "id": str(r.id),
                "scope": r.scope,
                "memory_type": r.memory_type,
                "content": r.content,
                "user_id": r.user_id,
                "retention_days": r.retention_days,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }


@router.post("")
def create_memory(
    body: MemoryCreateRequest,
    principal: PrincipalDep,
    session: SessionDep,
    request_id: RequestIdDep,
) -> dict:
    row = memory_service.create_memory(
        session,
        principal=principal,
        content=body.content,
        memory_type=body.memory_type,
        scope=body.scope,
        retention_days=body.retention_days,
        request_id=request_id,
    )
    return {
        "id": str(row.id),
        "scope": row.scope,
        "memory_type": row.memory_type,
        "content": row.content,
        "status": "created",
    }


@router.delete("/{memory_id}")
def delete_memory(
    memory_id: UUID,
    principal: PrincipalDep,
    session: SessionDep,
    request_id: RequestIdDep,
) -> dict:
    row = memory_service.delete_memory(
        session,
        principal=principal,
        memory_id=memory_id,
        request_id=request_id,
    )
    return {"id": str(row.id), "status": "deleted"}
