"""Input/output guardrails."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.exceptions import GuardrailError

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"reveal\s+(your\s+)?system\s+prompt", re.I),
    re.compile(r"exfiltrate|exfiltration", re.I),
    re.compile(r"sudo\s+rm\s+-rf", re.I),
]

_SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9]+"),
    re.compile(r"sk_test_[A-Za-z0-9]+"),
    re.compile(r"AWS_SECRET_ACCESS_KEY\s*="),
]


@dataclass(frozen=True, slots=True)
class GuardrailResult:
    allowed: bool
    reason: str | None = None


def check_user_input(text: str, *, max_length: int = 8000) -> GuardrailResult:
    if not text or not text.strip():
        return GuardrailResult(False, "Empty input")
    if len(text) > max_length:
        return GuardrailResult(False, "Input too long")
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(False, "Potential prompt injection detected")
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(False, "Secret material detected in input")
    return GuardrailResult(True)


def assert_user_input_allowed(text: str, *, max_length: int = 8000) -> None:
    result = check_user_input(text, max_length=max_length)
    if not result.allowed:
        raise GuardrailError(result.reason or "Input rejected", details={"stage": "input"})


def check_model_output(text: str) -> GuardrailResult:
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(False, "Secret material detected in output")
    return GuardrailResult(True)


def assert_output_allowed(text: str) -> None:
    result = check_model_output(text)
    if not result.allowed:
        raise GuardrailError(result.reason or "Output rejected", details={"stage": "output"})


def filter_citations(
    requested_ids: list[str],
    allowed_ids: set[str],
) -> list[str]:
    return [cid for cid in requested_ids if cid in allowed_ids]
