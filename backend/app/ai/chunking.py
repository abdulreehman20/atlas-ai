"""Chunking helpers with deterministic IDs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from uuid import UUID

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.parsing import ParsedDocument

CHUNKER_VERSION = "atlas-chunker-v1"


@dataclass(frozen=True, slots=True)
class TextChunk:
    chunk_id: str
    chunk_index: int
    text: str
    page_number: int | None
    section: str | None
    start_offset: int | None
    end_offset: int | None
    content_checksum: str


def chunk_document(
    parsed: ParsedDocument,
    *,
    document_version_id: UUID,
    chunk_size: int,
    chunk_overlap: int,
) -> list[TextChunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: list[TextChunk] = []

    index = 0
    for page in parsed.pages:
        if not page.text.strip():
            continue
        pieces = splitter.split_text(page.text)
        cursor = 0
        for piece in pieces:
            start = page.text.find(piece, cursor)
            end = start + len(piece) if start >= 0 else None
            if start >= 0:
                cursor = start + max(len(piece) - chunk_overlap, 1)
            checksum = hashlib.sha256(piece.encode("utf-8")).hexdigest()
            chunk_id = f"{document_version_id}:{index}"
            chunks.append(
                TextChunk(
                    chunk_id=chunk_id,
                    chunk_index=index,
                    text=piece,
                    page_number=page.page_number,
                    section=page.section,
                    start_offset=start if start >= 0 else None,
                    end_offset=end,
                    content_checksum=checksum,
                )
            )
            index += 1
    return chunks
