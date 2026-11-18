"""Chat / conversation services."""

from __future__ import annotations

import json
from collections.abc import Iterator
from uuid import UUID, uuid4

from sqlmodel import Session, select

from app.ai.chat_model import ChatModelClient
from app.ai.chains import RAGResult, iter_rag_tokens, run_rag
from app.ai.embeddings import EmbeddingClient
from app.ai.vector_store import VectorStoreClient
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.core.security import Principal
from app.db.models.conversation import Conversation
from app.db.models.enums import MessageRole, UsageOperation
from app.db.models.message import Message
from app.db.models.workspace import Workspace
from app.repositories import usage as usage_repo
from app.schemas.chat import ChatResponse, Citation
from app.services.entitlements import assert_can_chat


def list_conversations(session: Session, *, principal: Principal) -> list[Conversation]:
    statement = (
        select(Conversation)
        .where(
            Conversation.workspace_id == principal.workspace_id,
            Conversation.owner_user_id == principal.user_id,
        )
        .order_by(Conversation.updated_at.desc())
    )
    return list(session.exec(statement).all())


def get_conversation(
    session: Session,
    *,
    principal: Principal,
    conversation_id: UUID,
) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if (
        conversation is None
        or conversation.workspace_id != principal.workspace_id
        or conversation.owner_user_id != principal.user_id
    ):
        raise NotFoundError("Conversation not found")
    return conversation


def list_messages(session: Session, *, conversation_id: UUID) -> list[Message]:
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(session.exec(statement).all())


def chat(
    session: Session,
    settings: Settings,
    *,
    principal: Principal,
    message: str,
    conversation_id: UUID | None,
    chat_client: ChatModelClient,
    embeddings: EmbeddingClient,
    vectors: VectorStoreClient,
    request_id: str | None = None,
) -> ChatResponse:
    assert_can_chat(session, settings, organization_id=principal.organization_id)

    if conversation_id is None:
        conversation = Conversation(
            workspace_id=principal.workspace_id,
            organization_id=principal.organization_id,
            owner_user_id=principal.user_id,
            title=message[:80],
            thread_id=f"thr_{uuid4().hex}",
        )
        session.add(conversation)
        session.flush()
    else:
        conversation = get_conversation(
            session, principal=principal, conversation_id=conversation_id
        )

    user_message = Message(
        conversation_id=conversation.id,
        workspace_id=principal.workspace_id,
        role=MessageRole.USER.value,
        content=message,
        request_id=request_id,
    )
    session.add(user_message)

    workspace = session.get(Workspace, principal.workspace_id)
    result = run_rag(
        session,
        settings,
        workspace_id=principal.workspace_id,
        question=message,
        conversation_id=conversation.id,
        workspace_prompt_override=workspace.system_prompt_override if workspace else None,
        chat_client=chat_client,
        embeddings=embeddings,
        vectors=vectors,
        user_id=principal.user_id,
    )

    citations_payload = [
        Citation(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_version_id=c.document_version_id,
            title=c.title,
            page_number=c.page_number,
            section=c.section,
            excerpt=c.text[:280],
        ).model_dump(mode="json")
        for c in result.citations
    ]
    assistant = Message(
        conversation_id=conversation.id,
        workspace_id=principal.workspace_id,
        role=MessageRole.ASSISTANT.value,
        content=result.answer,
        citations=citations_payload,
        model_id=settings.openrouter_chat_model,
        prompt_version=result.prompt_version,
        request_id=request_id,
    )
    session.add(assistant)
    usage_repo.add_usage(
        session,
        workspace_id=principal.workspace_id,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        operation=UsageOperation.CHAT,
        model_id=settings.openrouter_chat_model,
        request_id=request_id,
    )
    session.commit()
    session.refresh(assistant)
    session.refresh(conversation)

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant.id,
        answer=result.answer,
        citations=[Citation.model_validate(item) for item in citations_payload],
        insufficient_evidence=result.insufficient_evidence,
        prompt_version=result.prompt_version,
    )


def stream_chat_sse(
    session: Session,
    settings: Settings,
    *,
    principal: Principal,
    message: str,
    conversation_id: UUID | None,
    chat_client: ChatModelClient,
    embeddings: EmbeddingClient,
    vectors: VectorStoreClient,
    request_id: str | None = None,
) -> Iterator[str]:
    """Yield SSE lines: token events, then a final validated citation payload."""

    assert_can_chat(session, settings, organization_id=principal.organization_id)

    if conversation_id is None:
        conversation = Conversation(
            workspace_id=principal.workspace_id,
            organization_id=principal.organization_id,
            owner_user_id=principal.user_id,
            title=message[:80],
            thread_id=f"thr_{uuid4().hex}",
        )
        session.add(conversation)
        session.flush()
    else:
        conversation = get_conversation(
            session, principal=principal, conversation_id=conversation_id
        )

    user_message = Message(
        conversation_id=conversation.id,
        workspace_id=principal.workspace_id,
        role=MessageRole.USER.value,
        content=message,
        request_id=request_id,
    )
    session.add(user_message)
    session.flush()

    yield f"data: {json.dumps({'type': 'meta', 'conversation_id': str(conversation.id)})}\n\n"

    workspace = session.get(Workspace, principal.workspace_id)
    result: RAGResult | None = None
    for item in iter_rag_tokens(
        session,
        settings,
        workspace_id=principal.workspace_id,
        question=message,
        conversation_id=conversation.id,
        workspace_prompt_override=workspace.system_prompt_override if workspace else None,
        chat_client=chat_client,
        embeddings=embeddings,
        vectors=vectors,
        user_id=principal.user_id,
    ):
        if isinstance(item, RAGResult):
            result = item
        else:
            yield f"data: {json.dumps({'type': 'token', 'text': item})}\n\n"

    assert result is not None
    citations_payload = [
        Citation(
            chunk_id=c.chunk_id,
            document_id=c.document_id,
            document_version_id=c.document_version_id,
            title=c.title,
            page_number=c.page_number,
            section=c.section,
            excerpt=c.text[:280],
        ).model_dump(mode="json")
        for c in result.citations
    ]
    assistant = Message(
        conversation_id=conversation.id,
        workspace_id=principal.workspace_id,
        role=MessageRole.ASSISTANT.value,
        content=result.answer,
        citations=citations_payload,
        model_id=settings.openrouter_chat_model,
        prompt_version=result.prompt_version,
        request_id=request_id,
    )
    session.add(assistant)
    usage_repo.add_usage(
        session,
        workspace_id=principal.workspace_id,
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        operation=UsageOperation.CHAT,
        model_id=settings.openrouter_chat_model,
        request_id=request_id,
    )
    session.commit()
    session.refresh(assistant)

    final = ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant.id,
        answer=result.answer,
        citations=[Citation.model_validate(item) for item in citations_payload],
        insufficient_evidence=result.insufficient_evidence,
        prompt_version=result.prompt_version,
    )
    yield f"data: {json.dumps({'type': 'final', 'payload': final.model_dump(mode='json')})}\n\n"
    yield "data: {\"type\": \"done\"}\n\n"
