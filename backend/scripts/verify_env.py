"""Verify Phase 2 environment variables are present for local development.

Does not call external APIs or print secret values.
Exit code 0 = all required keys present and non-empty.
Exit code 1 = missing/empty required keys or invalid embedding dimension.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_ROOT / ".env"

REQUIRED = [
    "APP_ENV",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_STORAGE_BUCKET",
    "DATABASE_URL",
    "MIGRATION_DATABASE_URL",
    "CHECKPOINT_DATABASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_CHAT_MODEL",
    "OPENROUTER_EMBEDDING_MODEL",
    "EMBEDDING_DIMENSION",
    "PINECONE_API_KEY",
    "PINECONE_INDEX_NAME",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "STRIPE_SECRET_KEY",
    "STRIPE_PRICE_ID",
]

# Auth verify needs at least one of these (checked separately).
AUTH_VERIFY_KEYS = (
    "SUPABASE_JWT_SECRET",
    "SUPABASE_JWKS_URL",
)

OPTIONAL = [
    "OPENROUTER_BASE_URL",
    "PINECONE_INDEX_HOST",
    "STRIPE_WEBHOOK_SECRET",
    "LANGSMITH_TRACING",
    "SUPABASE_JWT_SECRET",
    "SUPABASE_JWKS_URL",
    "SUPABASE_PUBLISHABLE_KEY",
    "SUPABASE_SECRET_KEY",
]


def main() -> int:
    if not ENV_PATH.exists():
        print(f"MISSING file: {ENV_PATH}")
        print("Copy .env.example to .env and fill values after Supabase/console provisioning.")
        return 1

    load_dotenv(ENV_PATH)

    def _missing(key: str) -> bool:
        value = os.getenv(key, "").strip()
        return not value or "<" in value or "USER:PASSWORD" in value or "YOUR-PASSWORD" in value

    missing: list[str] = [key for key in REQUIRED if _missing(key)]

    if all(_missing(key) for key in AUTH_VERIFY_KEYS):
        missing.append("SUPABASE_JWT_SECRET|SUPABASE_JWKS_URL")

    dim = os.getenv("EMBEDDING_DIMENSION", "").strip()
    if dim and dim != "2048":
        print(
            f"INVALID EMBEDDING_DIMENSION={dim!r}; "
            "expected 2048 for nvidia/nemotron-3-embed-1b:free"
        )
        return 1

    index = os.getenv("PINECONE_INDEX_NAME", "").strip()
    if index and "atlas-rag-index" not in index:
        print(f"WARN PINECONE_INDEX_NAME={index!r} does not look like atlas-rag-index-*")

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    if supabase_url and "supabase.co" not in supabase_url and "localhost" not in supabase_url:
        print(f"WARN SUPABASE_URL={supabase_url!r} does not look like a Supabase URL")

    if not os.getenv("PINECONE_INDEX_HOST", "").strip():
        print("WARN PINECONE_INDEX_HOST is empty (set from Pinecone console when available)")

    if not os.getenv("STRIPE_WEBHOOK_SECRET", "").strip():
        print(
            "WARN STRIPE_WEBHOOK_SECRET is empty (add in Phase 20 / after webhook endpoint exists)"
        )

    present_optional = [k for k in OPTIONAL if os.getenv(k, "").strip()]

    if missing:
        print("Phase 2 env verification FAILED")
        print("Missing or placeholder required keys:")
        for key in missing:
            print(f"  - {key}")
        print(f"Optional keys present: {len(present_optional)}/{len(OPTIONAL)}")
        return 1

    print("Phase 2 env verification PASSED")
    print(f"Required keys present: {len(REQUIRED)}")
    print(f"Optional keys present: {len(present_optional)}/{len(OPTIONAL)}")
    print("Note: presence check only — live API connectivity is not verified here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
