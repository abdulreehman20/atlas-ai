"""Conversation transcript routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import PrincipalDep, SessionDep
from app.schemas.chat import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
)
from app.services import chat as chat_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    principal: PrincipalDep,
    session: SessionDep,
) -> ConversationListResponse:
    items = chat_service.list_conversations(session, principal=principal)
    return ConversationListResponse(
        items=[ConversationResponse.model_validate(item) for item in items]
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: UUID,
    principal: PrincipalDep,
    session: SessionDep,
) -> ConversationDetailResponse:
    conversation = chat_service.get_conversation(
        session, principal=principal, conversation_id=conversation_id
    )
    messages = chat_service.list_messages(session, conversation_id=conversation.id)
    return ConversationDetailResponse(
        conversation=ConversationResponse.model_validate(conversation),
        messages=[MessageResponse.model_validate(message) for message in messages],
    )
