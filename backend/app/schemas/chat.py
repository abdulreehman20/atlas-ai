"""Chat and conversation schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class Citation(APIModel):
    chunk_id: str
    document_id: UUID
    document_version_id: UUID
    title: str
    page_number: int | None = None
    section: str | None = None
    excerpt: str


class ChatRequest(APIModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: UUID | None = None


class ChatResponse(APIModel):
    conversation_id: UUID
    message_id: UUID
    answer: str
    citations: list[Citation]
    insufficient_evidence: bool = False
    prompt_version: str


class ConversationResponse(APIModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(APIModel):
    items: list[ConversationResponse]


class MessageResponse(APIModel):
    id: UUID
    role: str
    content: str
    citations: list[Any] | None = None
    created_at: datetime


class ConversationDetailResponse(APIModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]


class FeedbackRequest(APIModel):
    conversation_id: UUID | None = None
    message_id: UUID | None = None
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=4000)


class FeedbackResponse(APIModel):
    id: UUID
    rating: int
