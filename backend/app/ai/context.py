"""Context engineering / token budgeting."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.memory import MemoryTurn
from app.ai.retrieval import RetrievedChunk


@dataclass(frozen=True, slots=True)
class BuiltContext:
    evidence_block: str
    history_block: str
    selected_chunk_ids: list[str]


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def build_context(
    *,
    chunks: list[RetrievedChunk],
    history: list[MemoryTurn],
    token_budget: int,
    max_history_turns: int,
) -> BuiltContext:
    reserved = 1500
    remaining = max(token_budget - reserved, 500)

    history_parts: list[str] = []
    for turn in history[-max_history_turns:]:
        piece = f"{turn.role}: {turn.content}"
        cost = _approx_tokens(piece)
        if cost > remaining // 3:
            break
        history_parts.append(piece)
        remaining -= cost

    evidence_parts: list[str] = []
    selected: list[str] = []
    for chunk in chunks:
        piece = (
            f"[chunk_id={chunk.chunk_id} title={chunk.title} "
            f"page={chunk.page_number}]\n{chunk.text}"
        )
        cost = _approx_tokens(piece)
        if cost > remaining:
            continue
        evidence_parts.append(piece)
        selected.append(chunk.chunk_id)
        remaining -= cost

    return BuiltContext(
        evidence_block="\n\n".join(evidence_parts) if evidence_parts else "(none)",
        history_block="\n".join(history_parts) if history_parts else "(none)",
        selected_chunk_ids=selected,
    )
