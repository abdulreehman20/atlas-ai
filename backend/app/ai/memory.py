"""Conversation memory helpers."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, select

from app.db.models.message import Message


@dataclass(frozen=True, slots=True)
class MemoryTurn:
    role: str
    content: str


def load_recent_turns(
    session: Session,
    *,
    conversation_id: UUID,
    max_turns: int,
) -> list[MemoryTurn]:
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(max_turns * 2)
    )
    rows = list(session.exec(statement).all())
    rows.reverse()
    return [MemoryTurn(role=row.role, content=row.content) for row in rows]
