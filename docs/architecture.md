# Atlas Enterprise AI — Architecture Baseline and ADRs

**Document version:** 1.1  
**Updated:** 2026-11-07  
**Related:** `requirements.md`, `supabase-migration.md`, `environments.md`

---

## 1. Architecture summary

```text
User
  └─ Next.js + Supabase Auth (@supabase/ssr)
       ├─ Supabase Storage (private uploads)
       └─ FastAPI (Supabase JWT Bearer)
            ├─ Supabase PostgreSQL (SQLModel / Alembic)
            ├─ Python ingestion worker (durable jobs)
            ├─ Amazon Bedrock (chat + embeddings)
            ├─ Pinecone (workspace namespaces)
            ├─ LangChain (RAG / memory / guardrails)
            ├─ LangSmith (traces)
            └─ Stripe (Checkout + webhooks)
```

FastAPI is the authorization and entitlement boundary. The frontend never decides tenant namespace, role, or paid access.

---

## 2. Platform constraints

| Constraint | Implication |
|---|---|
| Supabase Postgres | Use connection pooler for runtime; direct DB URL for migrations/checkpointer as required |
| Supabase JWT | Verify every protected request; use `sub` as identity |
| Supabase Storage RLS | Combine Storage policies with FastAPI ownership checks |
| Embedding dimension | Titan V2 @ 1024 must match Pinecone index |
| Ingestion | Durable Postgres job rows + Python worker (not in-request) |
| Stripe redirect ≠ payment | Entitlements only from verified webhooks |

---

## 3. Architecture Decision Records

### ADR-001 — Relational database: Supabase PostgreSQL

- **Status:** Accepted (amends prior Appwrite Managed PostgreSQL decision)
- **Context:** SQLModel/Alembic need a real PostgreSQL endpoint. Appwrite native Postgres unavailable on current plan; TablesDB incompatible.
- **Decision:** Use **Supabase PostgreSQL** as the application database.
- **Consequences:** Standard SQLAlchemy URLs, Alembic migrations, Postgres checkpointer. Appwrite is no longer used.

### ADR-002 — Ingestion worker: durable jobs + Python worker

- **Status:** Accepted (amends Appwrite Functions decision)
- **Context:** Heavy parsing/embedding must not run inside HTTP handlers. Supabase Edge Functions are Deno-first and a poor fit for the Python ingestion stack.
- **Decision:** FastAPI creates `ingestion_jobs`, commits, dispatches a **Python worker** under `workers/ingestion_worker` (same/shared services). Idempotent retries.
- **Consequences:** Deploy worker with FastAPI Cloud companion process, container, or scheduled runner; document in Phase 7.

### ADR-003 — Memory and HITL checkpointer

- **Status:** Accepted
- **Decision:** LangChain APIs + PostgreSQL checkpointer against Supabase Postgres. No custom LangGraph graphs. No `InMemorySaver` in production.

### ADR-004 — Pinecone workspace namespaces

- **Status:** Accepted
- **Decision:** Namespace `ws_{workspace_uuid}` server-side only + metadata filters.

### ADR-005 — Stripe webhook ownership: FastAPI only

- **Status:** Accepted
- **Decision:** Single webhook processor in FastAPI.

### ADR-006 — Frontend toolchain: Bun

- **Status:** Accepted

### ADR-007 — OCR out of first release

- **Status:** Accepted

### ADR-008 — Tenancy: Owner + Member, one workspace

- **Status:** Accepted

### ADR-009 — Prompt layering

- **Status:** Accepted — locked safety layer + Owner workspace override (Pro).

### ADR-010 — Entitlement enforcement (Option A)

- **Status:** Accepted — over quota blocks uploads + chat.

### ADR-011 — Identity and files: Supabase Auth + Storage

- **Status:** Accepted
- **Context:** Replace Appwrite Auth/Storage with Supabase for a single vendor covering Auth, DB, and Storage.
- **Decision:**
  - Auth: Supabase Auth; UI via shadcn; session/SSR via `@supabase/ssr`
  - Storage: private bucket `atlas-private-documents`
  - FastAPI verifies Supabase JWTs; uses service role only for privileged server operations
- **Consequences:** Env vars are `SUPABASE_*`. No Appwrite SDK in frontend or backend.

---

## 4. Security notes

- Keep `SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_JWT_SECRET` server-only.
- Only `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` may be public.
- Verify JWT on every protected API call; resolve membership in Postgres.
- Private Storage; validate MIME/size/checksum in FastAPI.
- Redact secrets and document text from LangSmith traces.
