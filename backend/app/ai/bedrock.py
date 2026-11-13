"""Amazon Bedrock chat model adapter (injectable)."""

from __future__ import annotations

from typing import Protocol

from langchain_aws import ChatBedrockConverse

from app.core.config import Settings


class ChatModelClient(Protocol):
    def generate(self, *, system: str, user: str) -> str: ...


class BedrockChatClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm: ChatBedrockConverse | None = None

    def _ensure_llm(self) -> ChatBedrockConverse:
        if self._llm is not None:
            return self._llm
        self._llm = ChatBedrockConverse(
            model=self._settings.bedrock_chat_model_id,
            region_name=self._settings.aws_region,
            temperature=0.1,
            max_tokens=2048,
        )
        return self._llm

    def generate(self, *, system: str, user: str) -> str:
        llm = self._ensure_llm()
        messages = [
            ("system", system),
            ("human", user),
        ]
        result = llm.invoke(messages)
        content = getattr(result, "content", result)
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
                else:
                    parts.append(str(item))
            return "".join(parts)
        return str(content)


class StubChatClient:
    """Deterministic chat client for unit tests."""

    def __init__(self, answer: str = "Based on the evidence, the answer is available.") -> None:
        self.answer = answer

    def generate(self, *, system: str, user: str) -> str:
        _ = system
        if "Evidence (untrusted source material):\n(none)" in user:
            return "I do not have enough evidence in the workspace documents to answer that."
        return self.answer
