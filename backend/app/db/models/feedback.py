"""User feedback on assistant answers."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Column, Text
from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Feedback(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "feedback"

    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    user_id: str = Field(max_length=128, index=True)
    conversation_id: UUID | None = Field(default=None, foreign_key="conversations.id")
    message_id: UUID | None = Field(default=None, foreign_key="messages.id")
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    review_state: str = Field(default="new", max_length=32)
