# Atlas Backend — API Testing Guide (FastAPI Swagger)

Use this guide to test every mounted backend API from **Swagger UI**.

| Item | Value |
|------|--------|
| Swagger UI | `http://127.0.0.1:8000/docs` |
| ReDoc | `http://127.0.0.1:8000/redoc` |
| OpenAPI JSON | `http://127.0.0.1:8000/openapi.json` |
| API prefix | `/api/v1` |
| Auth | Supabase JWT Bearer (`Authorization: Bearer <access_token>`) |

---

## 0. Start the backend

```powershell
cd backend
uv sync
fastapi dev app/main.py
```

Optional (document ingestion worker):

```powershell
uv run python scripts/run_ingestion_worker.py
```

Optional (one-time LangChain checkpointer schema):

```powershell
uv run python scripts/setup_checkpointer.py
```

Required env for real testing (see `docs/environments.md` / `backend/.env`):

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_JWT_SECRET` or `SUPABASE_JWKS_URL`
- `DATABASE_URL`
- For documents: `SUPABASE_SERVICE_ROLE_KEY`, storage bucket
- For chat/ingest: `OPENROUTER_API_KEY` + Pinecone keys (index dim **2048**)
- For billing: Stripe keys + price id

---

## 1. Swagger Authorize (do this first for protected APIs)

### Step A — Get a token

1. Open `http://127.0.0.1:8000/docs`
2. Expand **auth** → `POST /api/v1/auth/signup` (new user) **or** `POST /api/v1/auth/login` (existing)
3. Body:

```json
{
  "email": "abdulreehman104@gmail.com",
  "password": "YourStrongPass1"
}
```

4. Execute
5. Copy **only** `access_token` from the JSON response  
   - Do **not** paste `&expires_at=...&refresh_token=...` URL junk  
   - Do **not** type `Bearer ` yourself

### Step B — Authorize in Swagger

1. Click **Authorize** (lock icon at top)
2. Paste the JWT into **Value**
3. Click **Authorize** → **Close**

Swagger will send:

```http
Authorization: Bearer <access_token>
```

### Step C — Bootstrap Owner

Call **`GET /api/v1/me`**.

- First authenticated user with **no pending invite** → role `owner` (org + workspace created)
- Invited email → role `member` of the inviting workspace

Expect `200` and `"role": "owner"` for admin testing.

### Common headers

| Header | Required? | Notes |
|--------|-----------|--------|
| `Authorization: Bearer <token>` | Yes for protected routes | Set via Authorize |
| `Content-Type: application/json` | Yes for JSON bodies | Swagger sets automatically |
| `X-Request-ID` | Optional | Correlation / audit |

---

## 2. Recommended end-to-end test order

1. Health  
2. Auth → Authorize → `/me`  
3. Workspaces / members  
4. Documents → Storage upload → upload-complete → ingestion  
5. Chat (+ stream) → conversations → feedback  
6. Memory  
7. Approvals  
8. Usage  
9. Billing (if Stripe configured)

---

## 3. API reference

Legend:

- **Auth**: public = no Bearer needed; bearer = Authorize required; owner = Owner role only  
- Paths below are full paths including `/api/v1` unless noted (health is root)

---

### 3.1 Health (root — no `/api/v1`)

#### `GET /health/live`

| | |
|--|--|
| **Name** | Liveness |
| **Auth** | public |
| **Description** | Process is up |
| **Headers** | none |
| **Body** | none |
| **Expect** | `200` `{ "status": "ok", "checks": {} }` |

#### `GET /health/ready`

| | |
|--|--|
| **Name** | Readiness |
| **Auth** | public |
| **Description** | DB + JWT config checks |
| **Headers** | none |
| **Body** | none |
| **Expect** | `200` with `checks.database` = `ok` |

#### `GET /health/sentry-debug`

| | |
|--|--|
| **Name** | Sentry debug |
| **Auth** | public |
| **Description** | Deliberately raises `ZeroDivisionError` to verify Sentry |
| **Expect** | `500` (only use if Sentry DSN is set) |

---

### 3.2 Auth (`auth`)

#### `POST /api/v1/auth/signup`

| | |
|--|--|
| **Name** | Supabase signup |
| **Auth** | public |
| **Description** | Create Supabase Auth user |
| **Body** | |

```json
{
  "email": "owner@example.com",
  "password": "YourStrongPass1"
}
```

| **Expect** | `200` with `access_token`, `refresh_token`, `user` |
| **Notes** | If email confirm is ON in Supabase, `access_token` may be empty — confirm email or disable confirm for local tests, then use login |

#### `POST /api/v1/auth/login`

| | |
|--|--|
| **Name** | Password login |
| **Auth** | public |
| **Body** | |

```json
{
  "email": "owner@example.com",
  "password": "YourStrongPass1"
}
```

| **Expect** | `200` + `access_token` → paste into Authorize |

#### `POST /api/v1/auth/refresh`

| | |
|--|--|
| **Name** | Refresh session |
| **Auth** | public |
| **Body** | |

```json
{
  "refresh_token": "<refresh_token from login/signup>"
}
```

#### `POST /api/v1/auth/logout`

| | |
|--|--|
| **Name** | Logout |
| **Auth** | bearer |
| **Headers** | `Authorization: Bearer <access_token>` |
| **Body** | none |
| **Expect** | `200` `{ "status": "ok" }` |

#### `GET /api/v1/auth/user`

| | |
|--|--|
| **Name** | Current Supabase user |
| **Auth** | bearer |
| **Body** | none |
| **Expect** | `200` `{ "id", "email", "role", "user_metadata" }` |

---

### 3.3 Me (`me`)

#### `GET /api/v1/me`

| | |
|--|--|
| **Name** | Current principal |
| **Auth** | bearer |
| **Description** | Returns user, role, org, workspace, plan limits. Bootstraps Owner on first call |
| **Body** | none |
| **Expect** | |

```json
{
  "user_id": "...",
  "email": "...",
  "role": "owner",
  "organization": { "id": "...", "name": "..." },
  "workspace": { "id": "...", "name": "Default Workspace", "system_prompt_override": null },
  "member_count": 1,
  "plan": "free",
  "plan_tier": "free",
  "limits": {
    "members": 3,
    "documents": 20,
    "max_file_mib": 10,
    "storage_mib": 500,
    "chats_monthly": 100,
    "custom_prompt": false
  }
}
```

---

### 3.4 Workspaces (`workspaces`)

#### `GET /api/v1/workspaces/current`

| | |
|--|--|
| **Name** | Current workspace |
| **Auth** | bearer |
| **Body** | none |
| **Expect** | `organization_id`, `workspace_id`, `system_prompt_override` |

#### `PUT /api/v1/workspaces/current/system-prompt`

| | |
|--|--|
| **Name** | Update system prompt |
| **Auth** | owner |
| **Description** | Custom prompt requires **Pro** plan |
| **Body** | |

```json
{
  "system_prompt_override": "Answer briefly and cite sources."
}
```

| **Notes** | On Free plan expect `403` if non-null override |

#### `GET /api/v1/workspaces/current/members`

| | |
|--|--|
| **Name** | List members |
| **Auth** | bearer |
| **Body** | none |
| **Expect** | `{ "items": [ { "id", "user_id", "email", "role", "status" } ] }` |

#### `POST /api/v1/workspaces/current/members`

| | |
|--|--|
| **Name** | Invite member |
| **Auth** | owner |
| **Body** | |

```json
{
  "email": "member@example.com"
}
```

| **Expect** | `200` with `status: "invited"` |
| **How to finish invite** | Signup/login as that email → `GET /me` → same workspace, `role: "member"` |

#### `POST /api/v1/workspaces/current/members/accept`

| | |
|--|--|
| **Name** | Confirm invite accept |
| **Auth** | bearer |
| **Description** | Invite also auto-accepts on first authenticated call |
| **Body** | none |

#### `DELETE /api/v1/workspaces/current/members/{membership_id}`

| | |
|--|--|
| **Name** | Remove member |
| **Auth** | owner |
| **Path** | `membership_id` = UUID from list members |
| **Body** | none |
| **Expect** | `{ "id": "...", "status": "removed" }` |
| **Notes** | Cannot remove the owner |

---

### 3.5 Documents (`documents`)

Supported extensions: `.pdf`, `.txt`, `.md`, `.docx`, `.html`, `.htm`

#### `POST /api/v1/documents`

| | |
|--|--|
| **Name** | Create document (get storage path) |
| **Auth** | bearer |
| **Body** | |

```json
{
  "filename": "notes.txt",
  "size_bytes": 42,
  "mime_type": "text/plain",
  "title": "My notes"
}
```

| **Expect** | |

```json
{
  "id": "<document_uuid>",
  "storage_path": "<workspace_id>/<document_id>/notes.txt",
  "bucket": "atlas-private-documents",
  "status": "upload_pending"
}
```

#### Manual Storage upload (required between create and upload-complete)

Swagger cannot upload the binary to Supabase Storage. Outside Swagger:

1. Open Supabase Dashboard → Storage → bucket from response (`atlas-private-documents` by default)
2. Upload your file to the **exact** `storage_path`
3. File byte size should match `size_bytes` (upload-complete verifies size + optional checksum)

#### `POST /api/v1/documents/{document_id}/upload-complete`

| | |
|--|--|
| **Name** | Confirm upload + queue ingestion |
| **Auth** | bearer (owner or document owner) |
| **Body** | |

```json
{
  "storage_path": "<paste storage_path from create>",
  "checksum": null
}
```

Optional: set `checksum` to SHA-256 hex of file bytes.

| **Expect** | `{ "document_id", "job_id", "status": "queued" }` |
| **Errors** | `404` if object missing in Storage; `403` on size/checksum mismatch |

#### `GET /api/v1/documents`

| | |
|--|--|
| **Name** | List documents |
| **Auth** | bearer |
| **Body** | none |
| **Expect** | `{ "items": [ { "id", "title", "filename", "status", "size_bytes", ... } ] }` |

#### `POST /api/v1/documents/{document_id}/reprocess`

| | |
|--|--|
| **Name** | Re-queue ingestion |
| **Auth** | owner |
| **Body** | none |
| **Expect** | `{ "document_id", "job_id", "status": "queued" }` |

#### `DELETE /api/v1/documents/{document_id}`

| | |
|--|--|
| **Name** | Delete document |
| **Auth** | bearer (owner any doc; member own docs only) |
| **Description** | Soft-delete + Storage remove + Pinecone chunk cleanup |
| **Body** | none |
| **Expect** | `{ "id": "...", "status": "deleted" }` |

---

### 3.6 Ingestion (`ingestion`)

#### `GET /api/v1/ingestion/jobs/{job_id}`

| | |
|--|--|
| **Name** | Get ingestion job |
| **Auth** | bearer |
| **Body** | none |
| **Expect** | `{ "id", "document_id", "status", "attempt", "error_code", "error_message" }` |
| **Statuses** | `queued` → `running` → `succeeded` / `failed` |

#### `POST /api/v1/ingestion/jobs/{job_id}/run`

| | |
|--|--|
| **Name** | Run job now (owner) |
| **Auth** | owner |
| **Description** | Background process in non-test env; use worker for production-like flow |
| **Body** | none |
| **Expect** | Job payload; poll `GET .../jobs/{job_id}` until `succeeded` |
| **Then** | `GET /documents` → document `status` should be `ready` |

---

### 3.7 Chat (`chat`)

Requires ingested documents + OpenRouter/Pinecone for real answers (stubs in `APP_ENV=test`).

#### `POST /api/v1/chat`

| | |
|--|--|
| **Name** | Sync RAG chat |
| **Auth** | bearer |
| **Body** | |

```json
{
  "message": "What is covered in my notes?",
  "conversation_id": null
}
```

To continue a thread, set `conversation_id` from a previous response.

| **Expect** | |

```json
{
  "conversation_id": "...",
  "message_id": "...",
  "answer": "...",
  "citations": [],
  "insufficient_evidence": true,
  "prompt_version": "atlas-rag-v1"
}
```

#### `POST /api/v1/chat/stream`

| | |
|--|--|
| **Name** | Streaming RAG chat (SSE) |
| **Auth** | bearer |
| **Body** | same as `/chat` |
| **Expect** | `Content-Type: text/event-stream` with events: |

```text
data: {"type":"meta","conversation_id":"..."}
data: {"type":"token","text":"..."}
data: {"type":"final","payload":{ ... ChatResponse ... }}
data: {"type":"done"}
```

Swagger may show raw SSE text — that is normal.

---

### 3.8 Conversations (`conversations`)

#### `GET /api/v1/conversations`

| | |
|--|--|
| **Name** | List my conversations |
| **Auth** | bearer |
| **Body** | none |
| **Expect** | `{ "items": [ { "id", "title", "created_at", "updated_at" } ] }` |

#### `GET /api/v1/conversations/{conversation_id}`

| | |
|--|--|
| **Name** | Conversation + messages |
| **Auth** | bearer (own conversations only) |
| **Body** | none |
| **Expect** | `{ "conversation": {...}, "messages": [ { "id", "role", "content", "citations", "created_at" } ] }` |

---

### 3.9 Feedback (`feedback`)

#### `POST /api/v1/feedback`

| | |
|--|--|
| **Name** | Rate an answer |
| **Auth** | bearer |
| **Body** | |

```json
{
  "conversation_id": "<optional uuid>",
  "message_id": "<optional uuid from chat>",
  "rating": 5,
  "comment": "Helpful and grounded"
}
```

| **Expect** | `{ "id": "...", "rating": 5 }` |
| **Rules** | `rating` must be 1–5 |

---

### 3.10 Memory (`memory`)

Long-term memories are injected into later chat prompts.

#### `GET /api/v1/memory`

| | |
|--|--|
| **Name** | List memories |
| **Auth** | bearer |
| **Body** | none |

#### `POST /api/v1/memory`

| | |
|--|--|
| **Name** | Create memory |
| **Auth** | bearer (`scope: workspace` requires owner) |
| **Body** | |

```json
{
  "content": "Prefer short answers with citations",
  "memory_type": "preference",
  "scope": "user",
  "retention_days": 90
}
```

| **Expect** | `{ "id", "scope", "memory_type", "content", "status": "created" }` |

#### `DELETE /api/v1/memory/{memory_id}`

| | |
|--|--|
| **Name** | Soft-delete memory |
| **Auth** | bearer |
| **Body** | none |
| **Expect** | `{ "id": "...", "status": "deleted" }` |

---

### 3.11 Approvals / HITL (`approvals`)

Allowlisted `tool_name` values: `noop`, `document.delete`, `membership.remove`

#### `GET /api/v1/approvals`

| | |
|--|--|
| **Name** | List approvals |
| **Auth** | bearer |
| **Body** | none |

#### `POST /api/v1/approvals`

| | |
|--|--|
| **Name** | Create approval |
| **Auth** | bearer |
| **Smoke body** | |

```json
{
  "action": "test",
  "tool_name": "noop",
  "summary": "No-op approval for Swagger smoke test",
  "sanitized_arguments": {},
  "checkpoint_thread_id": null
}
```

**Document delete example:**

```json
{
  "action": "delete_document",
  "tool_name": "document.delete",
  "summary": "Delete document after owner approval",
  "sanitized_arguments": { "document_id": "<uuid>" }
}
```

**Membership remove example:**

```json
{
  "action": "remove_member",
  "tool_name": "membership.remove",
  "summary": "Remove invited/active member",
  "sanitized_arguments": { "membership_id": "<uuid>" }
}
```

#### `POST /api/v1/approvals/{approval_id}/decision`

| | |
|--|--|
| **Name** | Approve or reject (executes on approve) |
| **Auth** | owner |
| **Body** | |

```json
{
  "decision": "approve",
  "note": "Looks good"
}
```

or

```json
{
  "decision": "reject",
  "note": "Not needed"
}
```

| **Expect on approve** | status becomes `executed` (after allowlisted tool runs) |
| **Expect on reject** | status `rejected` |

---

### 3.12 Usage (`usage`)

#### `GET /api/v1/usage/summary`

| | |
|--|--|
| **Name** | Usage vs plan limits |
| **Auth** | owner |
| **Body** | none |
| **Expect** | `{ "plan", "usage": { chats, documents, storage_bytes, members }, "limits": {...}, "recent": [...] }` |

---

### 3.13 Billing (`billing`)

Requires Stripe env vars. Webhook is normally called by Stripe, not manually from Swagger.

#### `GET /api/v1/billing/subscription`

| | |
|--|--|
| **Name** | Subscription status |
| **Auth** | bearer |
| **Body** | none |
| **Expect** | `{ "status", "plan_tier", "stripe_price_id", "cancel_at_period_end" }` |

#### `POST /api/v1/billing/checkout`

| | |
|--|--|
| **Name** | Create Stripe Checkout session |
| **Auth** | owner |
| **Body** | none |
| **Expect** | `{ "checkout_url": "https://checkout.stripe.com/...", "id": "cs_..." }` |
| **Test** | Open `checkout_url` → pay with Stripe test card `4242 4242 4242 4242` |

#### `POST /api/v1/billing/portal`

| | |
|--|--|
| **Name** | Customer portal |
| **Auth** | owner |
| **Body** | none |
| **Expect** | `{ "portal_url": "..." }` |
| **Notes** | Needs an existing billing customer (after checkout) |

#### `POST /api/v1/billing/webhooks/stripe`

| | |
|--|--|
| **Name** | Stripe webhook |
| **Auth** | Stripe signature (not Bearer) |
| **Headers** | `stripe-signature: <Stripe-Signature>` |
| **Body** | raw Stripe event JSON |
| **How to test** | Use Stripe CLI: `stripe listen --forward-to localhost:8000/api/v1/billing/webhooks/stripe` |
| **Do not** | Call this from Swagger without a valid Stripe signature (`400`) |

---

## 4. Full happy-path checklist (Owner in Swagger)

Copy this and tick as you go:

- [ ] `GET /health/live` → ok  
- [ ] `GET /health/ready` → database ok  
- [ ] `POST /auth/signup` or `/auth/login` → copy `access_token`  
- [ ] Authorize in Swagger  
- [ ] `GET /me` → `role: owner`  
- [ ] `GET /workspaces/current`  
- [ ] `GET /workspaces/current/members`  
- [ ] `POST /documents` → save `id`, `storage_path`, `bucket`  
- [ ] Upload file to Supabase Storage at `storage_path`  
- [ ] `POST /documents/{id}/upload-complete` → save `job_id`  
- [ ] `POST /ingestion/jobs/{job_id}/run` (owner) **or** run worker  
- [ ] `GET /ingestion/jobs/{job_id}` → `succeeded`  
- [ ] `GET /documents` → `ready`  
- [ ] `POST /chat` → answer / citations  
- [ ] `POST /chat/stream` → SSE events  
- [ ] `GET /conversations` → open detail  
- [ ] `POST /feedback` with rating  
- [ ] `POST /memory` → `GET /memory`  
- [ ] `POST /approvals` (`noop`) → decide `approve` → `executed`  
- [ ] `GET /usage/summary`  
- [ ] (optional) `POST /billing/checkout` → Stripe test pay → `GET /billing/subscription`  
- [ ] (optional) invite member → member login → `GET /me` as member  

---

## 5. Role matrix (quick)

| Capability | Owner | Member |
|------------|-------|--------|
| `/me`, chat, list docs, upload own docs | yes | yes |
| Invite / remove members | yes | no |
| System prompt override | yes (Pro) | no |
| Reprocess document | yes | no |
| Run ingestion job via API | yes | no |
| Approve / reject HITL | yes | no |
| Usage summary | yes | no |
| Billing checkout / portal | yes | no |
| Delete any document | yes | own only |

---

## 6. Common errors

| Status | Meaning | What to check |
|--------|---------|----------------|
| `401` | Unauthorized | Token missing/expired — login again + Authorize |
| `403` | Forbidden | Wrong role / Free plan limit / not document owner |
| `404` | Not found | Bad UUID, wrong workspace, Storage object missing |
| `409` | Conflict | Member already invited |
| `402` | Entitlement exceeded | Plan quotas (members/docs/storage/chats) |
| `422` | Validation | Bad body / unsupported file extension |
| `503` | Dependency not configured | Supabase Auth / Stripe env missing |

---

## 7. Automated tests (optional)

From `backend/`:

```powershell
uv run pytest -q
```

These cover bootstrap, invite accept, document lifecycle, auth OpenAPI routes, memory, stream, and approval executor smoke paths.

---

## 8. Tips for Swagger testing

1. Always Authorize after login; tokens expire (~1 hour) — use `/auth/refresh` or login again.  
2. Paste **JWT only** (starts with `eyJ`, three dot-separated parts).  
3. Document upload is **two-step**: API create → Storage upload → upload-complete.  
4. Chat quality depends on OpenRouter (`nemotron` free models) + Pinecone (2048-d) + ingested `ready` docs.  
5. Prefer the **recommended order** in section 2 so later APIs have the data they need.
