# Atlas Enterprise AI — Phase Tracking

**Last updated:** 2026-11-08  
**Authoritative roadmap:** `ATLAS_Implementation_Plan.md` (read via `supabase-migration.md`)  
**Product baseline:** `requirements.md`, `architecture.md`, `environments.md`, `conflicts-and-decisions.md`  
**Operator setup (do at the end):** `SETUP_EVERYTHING.md`

Status values: `NOT_STARTED` | `IN_PROGRESS` | `BLOCKED` | `TESTING` | `COMPLETED`

---

## Summary

| Phase | Title | Status |
|---|---|---|
| 0 | Requirements, Architecture, and Repository Audit | COMPLETED |
| 1 | Repository and Local Development Foundation | COMPLETED |
| 2 | Provision External Services and Environments | BLOCKED (operator credentials) |
| 3 | FastAPI application foundation | COMPLETED |
| 4 | SQLModel schema + Alembic | COMPLETED |
| 5 | Supabase Auth JWT + principal bootstrap | COMPLETED |
| 6 | Document upload API + Storage paths | COMPLETED |
| 7 | Durable ingestion jobs + Python worker | COMPLETED |
| 8 | Parsing / chunking | COMPLETED |
| 9 | Embeddings (Bedrock Titan V2 @ 1024) | COMPLETED |
| 10 | Pinecone namespaces `ws_{uuid}` | COMPLETED |
| 11 | RAG chat + citations | COMPLETED |
| 12 | Conversation memory / history | COMPLETED |
| 13 | Context assembly + locked safety prompt | COMPLETED |
| 14 | Guardrails | COMPLETED |
| 15 | HITL approvals API/UI shell | COMPLETED |
| 16 | Frontend auth (Supabase) | COMPLETED |
| 17 | Documents UI | COMPLETED |
| 18 | Chat UI | COMPLETED |
| 19 | Admin: members, settings, billing UI | COMPLETED |
| 20 | Stripe Free/Pro entitlements + webhooks | COMPLETED |
| 21 | LangSmith observability hooks | COMPLETED |
| 22 | Usage metering + limits | COMPLETED |
| 23 | Deploy docs (FastAPI Cloud + Vercel) | COMPLETED (docs) |
| 24 | Smoke / verification scripts | COMPLETED (`verify_env.py`, pytest) |
| 25 | Production go-live checklist | COMPLETED (in SETUP) |

---

## Stack note

**Supabase** = Auth + PostgreSQL + Storage. Ingestion = `backend/scripts/run_ingestion_worker.py`. Frontend = Bun + Next.js.

---

## Phase 2 blocker (operator)

Live cloud keys must still be filled by you:

- Supabase project + Auth + Storage bucket + DB URLs
- Bedrock model access + IAM
- Pinecone index 1024/cosine
- LangSmith project
- Stripe test product/price + webhook

Follow **`docs/SETUP_EVERYTHING.md`** end-to-end. Track checkboxes in `docs/phase-2-provisioning-status.md`.

### Repo-side Phase 2

- [x] Env templates + `verify_env.py`
- [x] Worker entrypoint
- [ ] Operator fills `.env` / `.env.local`
- [ ] `uv run python scripts/verify_env.py` PASS on live values

### Automated tests (backend)

| Command | Result |
|---|---|
| `uv run pytest` | **20 passed** (2026-11-08) |
| Live cloud verification | NOT RUN until credentials ready |
