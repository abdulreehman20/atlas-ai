"""Pinecone vector store adapter (injectable)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from pinecone import Pinecone

from app.core.config import Settings
from app.core.security import pinecone_namespace


@dataclass(frozen=True, slots=True)
class VectorMatch:
    id: str
    score: float
    metadata: dict[str, Any]


class VectorStoreClient(Protocol):
    def upsert(
        self,
        *,
        workspace_id: UUID,
        vectors: list[tuple[str, list[float], dict[str, Any]]],
    ) -> None: ...

    def query(
        self,
        *,
        workspace_id: UUID,
        vector: list[float],
        top_k: int,
        filter: dict[str, Any] | None = None,
    ) -> list[VectorMatch]: ...

    def delete_ids(self, *, workspace_id: UUID, ids: list[str]) -> None: ...


class PineconeVectorStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._index = None

    def _ensure_index(self):
        if self._index is not None:
            return self._index
        client = Pinecone(api_key=self._settings.pinecone_api_key)
        if self._settings.pinecone_index_host:
            self._index = client.Index(host=self._settings.pinecone_index_host)
        else:
            self._index = client.Index(self._settings.pinecone_index_name)
        return self._index

    def upsert(
        self,
        *,
        workspace_id: UUID,
        vectors: list[tuple[str, list[float], dict[str, Any]]],
    ) -> None:
        if not vectors:
            return
        index = self._ensure_index()
        namespace = pinecone_namespace(workspace_id)
        payload = [
            {"id": vid, "values": values, "metadata": metadata} for vid, values, metadata in vectors
        ]
        index.upsert(vectors=payload, namespace=namespace)

    def query(
        self,
        *,
        workspace_id: UUID,
        vector: list[float],
        top_k: int,
        filter: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        index = self._ensure_index()
        namespace = pinecone_namespace(workspace_id)
        result = index.query(
            vector=vector,
            top_k=top_k,
            namespace=namespace,
            filter=filter,
            include_metadata=True,
        )
        matches = getattr(result, "matches", None) or result.get("matches", [])
        output: list[VectorMatch] = []
        for match in matches:
            mid = getattr(match, "id", None) or match.get("id")
            score = getattr(match, "score", None)
            if score is None:
                score = match.get("score", 0.0)
            metadata = getattr(match, "metadata", None)
            if metadata is None:
                metadata = match.get("metadata") or {}
            output.append(VectorMatch(id=str(mid), score=float(score), metadata=dict(metadata)))
        return output

    def delete_ids(self, *, workspace_id: UUID, ids: list[str]) -> None:
        if not ids:
            return
        index = self._ensure_index()
        index.delete(ids=ids, namespace=pinecone_namespace(workspace_id))


class InMemoryVectorStore:
    """Test double for Pinecone."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, tuple[list[float], dict[str, Any]]]] = {}

    def upsert(
        self,
        *,
        workspace_id: UUID,
        vectors: list[tuple[str, list[float], dict[str, Any]]],
    ) -> None:
        ns = pinecone_namespace(workspace_id)
        bucket = self._data.setdefault(ns, {})
        for vid, values, metadata in vectors:
            bucket[vid] = (values, metadata)

    def query(
        self,
        *,
        workspace_id: UUID,
        vector: list[float],
        top_k: int,
        filter: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        ns = pinecone_namespace(workspace_id)
        bucket = self._data.get(ns, {})
        scored: list[VectorMatch] = []
        for vid, (values, metadata) in bucket.items():
            if filter:
                if any(metadata.get(k) != v for k, v in filter.items()):
                    continue
            score = _cosine(vector, values)
            scored.append(VectorMatch(id=vid, score=score, metadata=metadata))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def delete_ids(self, *, workspace_id: UUID, ids: list[str]) -> None:
        ns = pinecone_namespace(workspace_id)
        bucket = self._data.get(ns, {})
        for vid in ids:
            bucket.pop(vid, None)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
