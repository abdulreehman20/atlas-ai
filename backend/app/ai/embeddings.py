"""Bedrock Titan embedding adapter (injectable)."""

from __future__ import annotations

from typing import Protocol

from langchain_aws import BedrockEmbeddings

from app.core.config import Settings


class EmbeddingClient(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class BedrockEmbeddingClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: BedrockEmbeddings | None = None

    def _ensure(self) -> BedrockEmbeddings:
        if self._client is not None:
            return self._client
        self._client = BedrockEmbeddings(
            model_id=self._settings.bedrock_embedding_model_id,
            region_name=self._settings.aws_region,
        )
        return self._client

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._ensure().embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._ensure().embed_query(text)


class StubEmbeddingClient:
    def __init__(self, dimension: int = 1024) -> None:
        self.dimension = dimension

    def _vector(self, text: str) -> list[float]:
        seed = sum(ord(ch) for ch in text) % 97
        return [((seed + i) % 97) / 97.0 for i in range(self.dimension)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)
