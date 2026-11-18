"""Grounded RAG chain (LangChain chain-first, no custom LangGraph)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from app.ai.chat_model import ChatModelClient
from app.ai.context import BuiltContext, build_context
from app.ai.embeddings import EmbeddingClient
from app.ai.guardrails import assert_output_allowed, assert_user_input_allowed, filter_citations
from app.ai.memory import load_recent_turns
from app.ai.prompts import RAG_USER_TEMPLATE, build_system_prompt
from app.ai.retrieval import RetrievedChunk, retrieve
from app.ai.vector_store import VectorStoreClient
from app.core.config import Settings
from app.services.memory_records import load_memory_snippets

_CHUNK_ID_RE = re.compile(
    r"chunk_id\s*=\s*([0-9a-fA-F-]{8,}(?::\d+)?)",
    re.IGNORECASE,
)
_SOURCES_LINE_RE = re.compile(
    r"(?im)^\s*(sources?|citations?)\s*:\s*.+$",
)
_INLINE_CHUNK_RE = re.compile(
    r"\s*[\(\[]\s*chunk_id\s*=\s*[^\]\)]+[\]\)]",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class RAGResult:
    answer: str
    citations: list[RetrievedChunk]
    insufficient_evidence: bool
    prompt_version: str


def _strip_chunk_markers(answer: str) -> str:
    """Remove model-emitted chunk_id / Sources lines — citations UI covers that."""
    text = _INLINE_CHUNK_RE.sub("", answer)
    text = _SOURCES_LINE_RE.sub("", text)
    text = _CHUNK_ID_RE.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _citations_for_answer(
    answer: str,
    chunks: list[RetrievedChunk],
    allowed: set[str],
) -> list[RetrievedChunk]:
    """Prefer chunks the model mentioned; else focus on the best-matching document."""
    mentioned = set(filter_citations(_CHUNK_ID_RE.findall(answer), allowed))
    if mentioned:
        return [chunk for chunk in chunks if chunk.chunk_id in mentioned]

    ranked = [chunk for chunk in chunks if chunk.chunk_id in allowed]
    if not ranked:
        return []
    ranked.sort(key=lambda item: item.score, reverse=True)
    best_document_id = ranked[0].document_id
    focused = [chunk for chunk in ranked if chunk.document_id == best_document_id]
    return focused[:5]


def _build_rag_prompt(
    session: Session,
    settings: Settings,
    *,
    workspace_id: UUID,
    user_id: str | None,
    question: str,
    conversation_id: UUID | None,
    workspace_prompt_override: str | None,
    embeddings: EmbeddingClient,
    vectors: VectorStoreClient,
) -> tuple[str, str, list[RetrievedChunk], BuiltContext]:
    assert_user_input_allowed(question)
    chunks = retrieve(
        session,
        workspace_id=workspace_id,
        query=question,
        top_k=settings.rag_top_k,
        embeddings=embeddings,
        vectors=vectors,
    )
    history = (
        load_recent_turns(
            session,
            conversation_id=conversation_id,
            max_turns=settings.memory_max_turns,
        )
        if conversation_id
        else []
    )
    context = build_context(
        chunks=chunks,
        history=history,
        token_budget=settings.context_token_budget,
        max_history_turns=settings.memory_max_turns,
    )
    system = build_system_prompt(
        workspace_override=workspace_prompt_override, prompt_version=settings.prompt_version
    )
    user = RAG_USER_TEMPLATE.format(question=question, evidence=context.evidence_block)

    if context.history_block != "(none)":
        user = f"Recent conversation:\n{context.history_block}\n\n{user}"

    if user_id:
        memories = load_memory_snippets(
            session, workspace_id=workspace_id, user_id=user_id, limit=8
        )
        if memories:
            user = "Approved long-term memories:\n" + "\n".join(memories) + "\n\n" + user

    return system, user, chunks, context


def run_rag(
    session: Session,
    settings: Settings,
    *,
    workspace_id: UUID,
    question: str,
    conversation_id: UUID | None,
    workspace_prompt_override: str | None,
    chat_client: ChatModelClient,
    embeddings: EmbeddingClient,
    vectors: VectorStoreClient,
    user_id: str | None = None,
) -> RAGResult:
    system, user, chunks, context = _build_rag_prompt(
        session,
        settings,
        workspace_id=workspace_id,
        user_id=user_id,
        question=question,
        conversation_id=conversation_id,
        workspace_prompt_override=workspace_prompt_override,
        embeddings=embeddings,
        vectors=vectors,
    )

    if not context.selected_chunk_ids:
        answer = "I do not have enough evidence in the workspace documents to answer that."
        assert_output_allowed(answer)
        return RAGResult(
            answer=answer,
            citations=[],
            insufficient_evidence=True,
            prompt_version=settings.prompt_version,
        )

    raw_answer = chat_client.generate(system=system, user=user)
    assert_output_allowed(raw_answer)
    allowed = set(context.selected_chunk_ids)
    cited = _citations_for_answer(raw_answer, chunks, allowed)
    answer = _strip_chunk_markers(raw_answer)

    return RAGResult(
        answer=answer,
        citations=cited,
        insufficient_evidence=False,
        prompt_version=settings.prompt_version,
    )


def iter_rag_tokens(
    session: Session,
    settings: Settings,
    *,
    workspace_id: UUID,
    question: str,
    conversation_id: UUID | None,
    workspace_prompt_override: str | None,
    chat_client: ChatModelClient,
    embeddings: EmbeddingClient,
    vectors: VectorStoreClient,
    user_id: str | None = None,
) -> Iterator[str | RAGResult]:
    """Yield answer token strings, then a final RAGResult."""

    system, user, chunks, context = _build_rag_prompt(
        session,
        settings,
        workspace_id=workspace_id,
        user_id=user_id,
        question=question,
        conversation_id=conversation_id,
        workspace_prompt_override=workspace_prompt_override,
        embeddings=embeddings,
        vectors=vectors,
    )

    if not context.selected_chunk_ids:
        answer = "I do not have enough evidence in the workspace documents to answer that."
        assert_output_allowed(answer)
        yield answer
        yield RAGResult(
            answer=answer,
            citations=[],
            insufficient_evidence=True,
            prompt_version=settings.prompt_version,
        )
        return

    parts: list[str] = []
    for token in chat_client.stream(system=system, user=user):
        parts.append(token)
        yield token
    raw_answer = "".join(parts)
    assert_output_allowed(raw_answer)
    allowed = set(context.selected_chunk_ids)
    cited = _citations_for_answer(raw_answer, chunks, allowed)
    yield RAGResult(
        answer=_strip_chunk_markers(raw_answer),
        citations=cited,
        insufficient_evidence=False,
        prompt_version=settings.prompt_version,
    )
