"""Chat model adapter — OpenRouter via LangChain ChatOpenAI."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _content_to_text(content: object) -> str:
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


class ChatModelClient(Protocol):
    def generate(self, *, system: str, user: str) -> str: ...

    def stream(self, *, system: str, user: str) -> Iterator[str]: ...


class OpenRouterChatClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm: ChatOpenAI | None = None

    def _ensure_llm(self) -> ChatOpenAI:
        if self._llm is not None:
            return self._llm
        if not self._settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")
        logger.info(
            "Initializing OpenRouter chat model=%s",
            self._settings.openrouter_chat_model,
        )
        self._llm = ChatOpenAI(
            model=self._settings.openrouter_chat_model,
            api_key=self._settings.openrouter_api_key,
            base_url=self._settings.openrouter_base_url,
            temperature=0.1,
            max_tokens=self._settings.chat_max_tokens,
            default_headers={
                "HTTP-Referer": self._settings.frontend_url,
                "X-Title": self._settings.app_name,
            },
        )
        return self._llm

    def generate(self, *, system: str, user: str) -> str:
        llm = self._ensure_llm()
        result = llm.invoke(
            [
                ("system", system),
                ("human", user),
            ]
        )
        return _content_to_text(getattr(result, "content", result))

    def stream(self, *, system: str, user: str) -> Iterator[str]:
        llm = self._ensure_llm()
        for chunk in llm.stream(
            [
                ("system", system),
                ("human", user),
            ]
        ):
            text = _content_to_text(getattr(chunk, "content", chunk))
            if text:
                yield text


class StubChatClient:
    """Deterministic chat client for unit tests."""

    def __init__(self, answer: str = "Based on the evidence, the answer is available.") -> None:
        self.answer = answer

    def generate(self, *, system: str, user: str) -> str:
        _ = system
        if "Evidence (untrusted source material):\n(none)" in user:
            return "I do not have enough evidence in the workspace documents to answer that."
        return self.answer

    def stream(self, *, system: str, user: str) -> Iterator[str]:
        answer = self.generate(system=system, user=user)
        mid = max(1, len(answer) // 2)
        yield answer[:mid]
        if answer[mid:]:
            yield answer[mid:]
