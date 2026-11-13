"""Chat transcript message."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import MessageRole


class Message(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "messages"

    conversation_id: UUID = Field(foreign_key="conversations.id", index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    role: str = Field(default=MessageRole.USER.value, max_length=32)
    content: str = Field(sa_column=Column(Text, nullable=False))
    citations: list | dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    model_id: str | None = Field(default=None, max_length=128)
    prompt_version: str | None = Field(default=None, max_length=64)
    token_usage: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    request_id: str | None = Field(default=None, max_length=128)
