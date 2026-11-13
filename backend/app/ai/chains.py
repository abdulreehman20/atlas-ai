"""Grounded RAG chain (LangChain chain-first, no custom LangGraph)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from app.ai.bedrock import ChatModelClient
from app.ai.context import build_context
from app.ai.embeddings import EmbeddingClient
from app.ai.guardrails import assert_output_allowed, assert_user_input_allowed, filter_citations
from app.ai.memory import load_recent_turns
from app.ai.prompts import RAG_USER_TEMPLATE, build_system_prompt
from app.ai.retrieval import RetrievedChunk, retrieve
from app.ai.vector_store import VectorStoreClient
from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class RAGResult:
    answer: str
    citations: list[RetrievedChunk]
    insufficient_evidence: bool
    prompt_version: str


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
) -> RAGResult:

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

    if not context.selected_chunk_ids:
        answer = "I do not have enough evidence in the workspace documents to answer that."
        assert_output_allowed(answer)
        return RAGResult(
            answer=answer,
            citations=[],
            insufficient_evidence=True,
            prompt_version=settings.prompt_version,
        )

    answer = chat_client.generate(system=system, user=user)
    assert_output_allowed(answer)
    allowed = set(context.selected_chunk_ids)

    # Keep citations tied to retrieved evidence only.
    cited = [chunk for chunk in chunks if chunk.chunk_id in allowed]
    _ = filter_citations([c.chunk_id for c in cited], allowed)

    return RAGResult(
        answer=answer,
        citations=cited,
        insufficient_evidence=False,
        prompt_version=settings.prompt_version,
    )
