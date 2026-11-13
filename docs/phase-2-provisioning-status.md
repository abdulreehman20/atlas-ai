# Phase 2 — Live provisioning status (Supabase stack)

**Updated:** 2026-11-07  
**Overall:** `BLOCKED` — waiting on operator console provisioning  
**Platform:** Supabase (Auth + PostgreSQL + Storage) — see `supabase-migration.md`

Do not paste secrets into this file.

| Service | Status | Notes |
|---|---|---|
| Supabase project (dev) | PENDING | `atlas-enterprise-ai-dev` |
| Supabase Auth email/password | PENDING | Site URL `http://localhost:3000` |
| Supabase PostgreSQL URLs | PENDING | pooler + direct |
| Supabase Storage bucket | PENDING | `atlas-private-documents` private |
| Supabase keys in `.env` | PENDING | URL, anon, service role, JWT secret |
| AWS Bedrock model access | PENDING | Nova Lite + Titan Embed V2 |
| AWS IAM for Atlas | PENDING | `docs/iam/bedrock-atlas-dev.json` |
| Pinecone index `atlas-rag-index-dev` | PENDING | dim=1024, cosine |
| LangSmith projects | PENDING | |
| Stripe test product Atlas Pro | PENDING | |
| `uv run python scripts/verify_env.py` | PENDING | |

## Recorded non-secret values

| Field | Value |
|---|---|
| Supabase project URL | |
| Supabase region | |
| Storage bucket | `atlas-private-documents` |
| AWS region | |
| Pinecone index name | `atlas-rag-index-dev` |
| Pinecone index host | |
| Stripe Price ID (Pro) | |
| LangSmith project | `atlas-enterprise-ai-dev` |
