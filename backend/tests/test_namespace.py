"""Pinecone namespace derivation tests."""

from __future__ import annotations

from uuid import UUID

from app.core.security import pinecone_namespace


def test_pinecone_namespace_format() -> None:
    workspace_id = UUID("12345678-1234-5678-1234-567812345678")
    assert pinecone_namespace(workspace_id) == "ws_12345678-1234-5678-1234-567812345678"


def test_pinecone_namespace_never_from_client_string_alone() -> None:
    # Helper always prefixes ws_; callers must pass trusted workspace UUID.
    assert pinecone_namespace("abc").startswith("ws_")
