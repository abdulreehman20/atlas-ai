# Technology Amendment — Appwrite → Supabase

**Effective:** 2026-11-07  
**Status:** Binding product/architecture decision  
**Reason:** Appwrite Managed PostgreSQL (native) is unavailable on the current Appwrite plan; TablesDB is incompatible with SQLModel/Alembic. Supabase provides Auth, PostgreSQL, and Storage in one stack that matches Atlas persistence requirements.

## Binding replacements

| Former (Appwrite) | New (Supabase) |
|---|---|
| Appwrite Auth | **Supabase Auth** (email/password; SSR via `@supabase/ssr`) |
| Appwrite Managed PostgreSQL | **Supabase PostgreSQL** (SQLModel + Alembic + checkpointer) |
| Appwrite Storage | **Supabase Storage** (private buckets) |
| Appwrite Functions (ingestion) | **Python ingestion worker** (`workers/ingestion_worker`) sharing backend services; optional Supabase Edge Functions only for light Deno tasks (not the primary Python pipeline) |
| Appwrite JWT → FastAPI | **Supabase access token** (`Authorization: Bearer`) verified with project JWT secret / JWKS |
| `APPWRITE_*` env vars | `SUPABASE_*` + Supabase `DATABASE_URL` variants |

## Unchanged

- FastAPI as application backend and entitlement authority
- LangChain, Amazon Bedrock, Pinecone, LangSmith, Stripe
- Owner + Member roles, single workspace, Option A billing
- Pinecone namespace `ws_{workspace_uuid}`
- Frontend: Next.js + Bun + shadcn/ui
- Deploy: FastAPI Cloud + Vercel

## Authority

This amendment overrides Appwrite-specific requirements in older sections of:

- `ATLAS_Implementation_Plan.md`
- `Atlas_Implementation_Steps.md`
- `Atlas_Documentation.md`

When those files still mention Appwrite, interpret them through this mapping unless a section was already rewritten. Prefer `requirements.md`, `architecture.md`, and `environments.md` for current truth.
