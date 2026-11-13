"""Chat RAG endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import (
    ChatClientDep,
    EmbeddingClientDep,
    PrincipalDep,
    RequestIdDep,
    SessionDep,
    SettingsDep,
    VectorStoreDep,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import chat as chat_service

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
def post_chat(
    body: ChatRequest,
    principal: PrincipalDep,
    session: SessionDep,
    settings: SettingsDep,
    chat_client: ChatClientDep,
    embeddings: EmbeddingClientDep,
    vectors: VectorStoreDep,
    request_id: RequestIdDep,
) -> ChatResponse:
    return chat_service.chat(
        session,
        settings,
        principal=principal,
        message=body.message,
        conversation_id=body.conversation_id,
        chat_client=chat_client,
        embeddings=embeddings,
        vectors=vectors,
        request_id=request_id,
    )
