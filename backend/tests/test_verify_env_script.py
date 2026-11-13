"""Tests for the Phase 2 env verification helper."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "verify_env.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_env", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_env"] = module
    spec.loader.exec_module(module)
    return module


def test_verify_env_fails_without_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "ENV_PATH", tmp_path / ".env")
    assert module.main() == 1


def test_verify_env_passes_with_required_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    env_file = tmp_path / ".env"
    lines = [
        "APP_ENV=development",
        "SUPABASE_URL=https://abc.supabase.co",
        "SUPABASE_ANON_KEY=anon",
        "SUPABASE_SERVICE_ROLE_KEY=service",
        "SUPABASE_JWKS_URL=https://abc.supabase.co/auth/v1/.well-known/jwks.json",
        "SUPABASE_STORAGE_BUCKET=atlas-private-documents",
        "DATABASE_URL=postgresql+psycopg://u:p@h:6543/postgres?sslmode=require",
        "MIGRATION_DATABASE_URL=postgresql+psycopg://u:p@h:5432/postgres?sslmode=require",
        "CHECKPOINT_DATABASE_URL=postgresql://u:p@h:5432/postgres?sslmode=require",
        "AWS_REGION=us-east-1",
        "BEDROCK_CHAT_MODEL_ID=amazon.nova-lite-v1:0",
        "BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0",
        "EMBEDDING_DIMENSION=1024",
        "PINECONE_API_KEY=pc-test",
        "PINECONE_INDEX_NAME=atlas-rag-index-dev",
        "LANGSMITH_API_KEY=ls-test",
        "LANGSMITH_PROJECT=atlas-enterprise-ai-dev",
        "STRIPE_SECRET_KEY=sk_test_x",
        "STRIPE_PRICE_ID=price_test",
    ]
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(module, "ENV_PATH", env_file)
    for key in module.REQUIRED:
        monkeypatch.delenv(key, raising=False)
    assert module.main() == 0
