"""Long-term memory record CRUD (workspace-scoped)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, col, select

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import Principal
from app.db.models.memory_record import MemoryRecord
from app.services.audit import record_audit


def list_memories(
    session: Session,
    *,
    principal: Principal,
    user_scoped: bool = True,
) -> list[MemoryRecord]:
    statement = select(MemoryRecord).where(
        MemoryRecord.workspace_id == principal.workspace_id,
        MemoryRecord.is_deleted == False,  # noqa: E712
    )
    if user_scoped:
        statement = statement.where(
            or_(MemoryRecord.user_id == principal.user_id, MemoryRecord.scope == "workspace")
        )
    statement = statement.order_by(col(MemoryRecord.created_at).desc())
    return list(session.exec(statement).all())


def create_memory(
    session: Session,
    *,
    principal: Principal,
    content: str,
    memory_type: str = "preference",
    scope: str = "user",
    retention_days: int | None = None,
    request_id: str | None = None,
) -> MemoryRecord:
    if scope not in {"user", "workspace"}:
        raise ForbiddenError("scope must be user or workspace")
    if scope == "workspace" and principal.role != "owner":
        raise ForbiddenError("Only owners may create workspace-scoped memories")

    row = MemoryRecord(
        workspace_id=principal.workspace_id,
        organization_id=principal.organization_id,
        user_id=principal.user_id if scope == "user" else None,
        scope=scope,
        memory_type=memory_type,
        content=content.strip(),
        retention_days=retention_days,
        consent_granted=True,
    )
    session.add(row)
    record_audit(
        session,
        action="memory.create",
        actor_user_id=principal.user_id,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        target_type="memory_record",
        request_id=request_id,
    )
    session.commit()
    session.refresh(row)
    return row


def delete_memory(
    session: Session,
    *,
    principal: Principal,
    memory_id: UUID,
    request_id: str | None = None,
) -> MemoryRecord:
    row = session.get(MemoryRecord, memory_id)
    if row is None or row.workspace_id != principal.workspace_id or row.is_deleted:
        raise NotFoundError("Memory not found")
    if row.scope == "user" and row.user_id != principal.user_id and principal.role != "owner":
        raise ForbiddenError("Cannot delete another user's memory")
    if row.scope == "workspace" and principal.role != "owner":
        raise ForbiddenError("Only owners may delete workspace memories")

    row.is_deleted = True
    session.add(row)
    record_audit(
        session,
        action="memory.delete",
        actor_user_id=principal.user_id,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        target_type="memory_record",
        target_id=str(row.id),
        request_id=request_id,
    )
    session.commit()
    session.refresh(row)
    return row


def load_memory_snippets(
    session: Session,
    *,
    workspace_id: UUID,
    user_id: str,
    limit: int = 8,
) -> list[str]:
    statement = (
        select(MemoryRecord)
        .where(
            MemoryRecord.workspace_id == workspace_id,
            MemoryRecord.is_deleted == False,  # noqa: E712
            or_(MemoryRecord.user_id == user_id, MemoryRecord.scope == "workspace"),
        )
        .order_by(col(MemoryRecord.created_at).desc())
        .limit(limit)
    )
    rows = list(session.exec(statement).all())
    return [f"[{r.memory_type}] {r.content}" for r in rows]
