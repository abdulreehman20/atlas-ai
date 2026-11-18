# Atlas Enterprise AI — Phase 0 Requirements Baseline

**Document version:** 1.1  
**Updated:** 2026-11-07  
**Status:** Binding  
**Stack amendment:** Supabase replaces Appwrite for Auth, Database, and Storage — see `supabase-migration.md`.

---

## 1. Repository status (current)

| Item | Finding |
|---|---|
| Repository | `rag-advance` (git initialized) |
| Backend | `uv` + Python 3.12 foundation (Phase 1) |
| Frontend | Next.js + Bun + shadcn shell (Phase 1) |
| Platform | **Supabase** Auth + PostgreSQL + Storage |
| Phase 2 | External provisioning in progress |

---

## 2. Tenant and workspace model

| Decision | Value |
|---|---|
| Organization | Created when a user signs up and becomes Owner |
| Workspace | **One workspace per organization** in v1 |
| Multi-workspace | Deferred |
| Membership | Per organization/workspace; Owner invites Members by email |
| Identity | Supabase Auth user ID (`auth.users` / JWT `sub`) |
| Vector isolation | Server-derived Pinecone namespace `ws_{workspace_uuid}` |
| Client trust | Browser-supplied tenant IDs, roles, namespaces, entitlements are never authoritative |

---

## 3. Roles and permissions matrix (v1)

| Capability | Owner | Member |
|---|---|---|
| Create organization (on signup) | Yes | No |
| Pay / manage Stripe subscription | Yes | No |
| Invite / remove members | Yes | No |
| Change another user's role | No | No |
| Settings / workspace system prompt | Yes | No |
| Billing section | Yes | No |
| Upload / view documents | Yes | Yes |
| Chat / Q&A | Yes | Yes |
| Delete own uploads | Yes | Yes |
| Delete any workspace document | Yes | No |
| Reprocess documents | Yes | No |
| Bulk document operations | No | No |

---

## 4. Document access model (v1)

| Rule | Decision |
|---|---|
| Visibility | Workspace-wide |
| Formats | PDF (text), TXT, MD, DOCX, HTML |
| OCR | Out of scope for v1 |
| Storage | Private **Supabase Storage** bucket `atlas-private-documents` |
| Max file (bucket) | 25 MiB; plan entitlements may be lower (Free 10 MiB) |

---

## 5. System prompt policy

| Layer | Owner-editable? |
|---|---|
| Platform safety / guardrails | **No** (locked) |
| Workspace instruction override | **Yes** (Pro plan) |

---

## 6. HITL scope (v1)

Member/owner document delete and membership admin are **direct authorized APIs with audit logs**. LangChain HITL remains for future sensitive agent tools. No bulk ops.

---

## 7. Billing (Option A)

| Limit | Free / Trial | Pro |
|---|---|---|
| Members | 3 | 25 |
| Documents | 20 | 500 |
| Max file size | 10 MiB | 25 MiB |
| Storage | 500 MiB | 20 GiB |
| Chat / month | 100 | 5,000 |
| Custom system prompt | No | Yes |
| Price | $0 | $49 / org / month |

Over-limit: **block new uploads and new chat**; existing content remains visible.

---

## 8. Platform & integration requirements

| Area | Technology |
|---|---|
| Auth | Supabase Auth (email/password); Next.js via `@supabase/ssr` + `@supabase/supabase-js` |
| Database | Supabase PostgreSQL via SQLModel + Alembic |
| File storage | Supabase Storage (private) |
| API | FastAPI — verifies Supabase JWT, owns authorization |
| Ingestion worker | Python worker (`workers/ingestion_worker`), durable jobs in Postgres |
| Vectors | Pinecone |
| LLM / embeddings | Amazon Bedrock |
| Observability | LangSmith |
| Payments | Stripe |
| Frontend | Next.js App Router + TypeScript + shadcn/ui + Bun |
| Deploy | FastAPI Cloud + Vercel |

---

## 9. Auth flow (Supabase)

1. User signs in with Supabase Auth in Next.js.
2. Frontend sends Supabase **access token** to FastAPI as `Authorization: Bearer <token>`.
3. FastAPI verifies the JWT (project JWT secret or JWKS) and reads `sub` as the user id.
4. FastAPI resolves organization/workspace membership from PostgreSQL.
5. Never trust client-supplied org/workspace/role/namespace.

Store Supabase user IDs as external identity references. Do not duplicate passwords in application tables.

---

## 10. Protected resource ownership

| Resource | Owner / scope |
|---|---|
| Organization / workspace | Creating user (Owner) |
| Membership | Org/workspace + Supabase user id |
| Document | Workspace; upload actor = document owner |
| Storage object | Supabase Storage path scoped to workspace; policies + FastAPI checks |
| Conversation | Workspace + user |
| Billing | Organization |
| Pinecone namespace | Derived from workspace id on server |

---

## 11. Explicit non-goals (v1)

- Appwrite Auth / Storage / Managed PostgreSQL / TablesDB
- OCR, multi-workspace, extra roles, bulk document ops
- Custom LangGraph workflow authoring
