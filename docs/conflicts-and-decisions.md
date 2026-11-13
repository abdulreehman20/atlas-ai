# Atlas Enterprise AI — Conflicts and Resolved Decisions

**Document version:** 1.1  
**Updated:** 2026-11-07

---

## C-001 — Frontend package manager

**Resolution:** **Bun** (ADR-006).

---

## C-002 — SSR / public auth env naming

**Resolution:** Supabase public values use `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`. Server-only: `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`.

---

## C-003 — Role model

**Resolution:** Owner + Member only (ADR-008).

---

## C-004 — Multi-workspace

**Resolution:** 1 org : 1 workspace in v1.

---

## C-005 — HITL for deletes / membership

**Resolution:** Direct authorized APIs + audit in v1; LangChain HITL for future agent tools.

---

## C-006 — Ingestion worker

**Resolution:** Python durable worker (`workers/ingestion_worker`), not Appwrite Functions / not primary Deno Edge Functions (ADR-002).

---

## C-007 — Billing limits

**Resolution:** Option A Free + Pro; over-limit blocks uploads + chat (ADR-010).

---

## C-008 — Appwrite → Supabase (Auth, DB, Storage)

| Source | Statement |
|---|---|
| Original plan / setup / overview | Appwrite Auth, Managed PostgreSQL, Storage, Functions |
| Appwrite Console (operator) | Native PostgreSQL locked behind upgrade; TablesDB only |
| Product decision 2026-11-07 | **Use Supabase** for Auth + PostgreSQL + Storage |

**Resolution:** Binding. See `supabase-migration.md` and ADR-001 / ADR-011.  
**Do not** use Appwrite TablesDB.  
**Do not** keep a hybrid Appwrite Auth + Supabase DB unless a future ADR explicitly reintroduces it.

---

## Priority rule

1. `supabase-migration.md`, `requirements.md`, `architecture.md`, `environments.md`
2. Phase tracking / this conflicts file
3. Older Appwrite wording in the long-form plan/setup/overview docs → apply the Supabase mapping
