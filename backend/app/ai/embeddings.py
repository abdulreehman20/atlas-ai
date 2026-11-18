"""Embedding adapter — OpenRouter via LangChain OpenAIEmbeddings."""

from __future__ import annotations

from typing import Protocol

from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingClient(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class OpenRouterEmbeddingClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: OpenAIEmbeddings | None = None

    def _ensure(self) -> OpenAIEmbeddings:
        if self._client is not None:
            return self._client
        if not self._settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")
        logger.info(
            "Initializing OpenRouter embeddings model=%s dim=%s",
            self._settings.openrouter_embedding_model,
            self._settings.embedding_dimension,
        )
        # Nemotron 3 Embed 1B is native 2048-d; do not pass reduced dimensions.
        self._client = OpenAIEmbeddings(
            model=self._settings.openrouter_embedding_model,
            api_key=self._settings.openrouter_api_key,
            base_url=self._settings.openrouter_base_url,
            check_embedding_ctx_length=False,
            default_headers={
                "HTTP-Referer": self._settings.frontend_url,
                "X-Title": self._settings.app_name,
            },
        )
        return self._client

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._ensure().embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._ensure().embed_query(text)


class StubEmbeddingClient:
    def __init__(self, dimension: int = 2048) -> None:
        self.dimension = dimension

    def _vector(self, text: str) -> list[float]:
        seed = sum(ord(ch) for ch in text) % 97
        return [((seed + i) % 97) / 97.0 for i in range(self.dimension)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)
