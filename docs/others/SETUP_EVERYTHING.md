# Atlas Enterprise AI — Complete Setup Guide (Do This At The End)

**Purpose:** One checklist for every console/credential/deploy step after the codebase is implemented.  
**Stack:** Supabase (Auth + Postgres + Storage) · FastAPI · Next.js (Bun) · Bedrock · Pinecone · LangSmith · Stripe · FastAPI Cloud · Vercel

Do **not** put secrets in git. Use `backend/.env` and `frontend/.env.local` only.

---

## 0. Local prerequisites

```powershell
python --version   # 3.12+ via uv
uv --version
node --version
bun --version
git --version
```

```powershell
cd backend
uv sync
Copy-Item .env.example .env   # if needed

cd ../frontend
bun install
Copy-Item .env.example .env.local
```

---

## 1. Supabase

1. Create project (e.g. `atlas-enterprise-ai-dev`) in [Supabase](https://supabase.com/dashboard).
2. **Authentication → Providers:** enable Email.
3. **Authentication → URL configuration:**
   - Site URL: `http://localhost:3000` (later: your Vercel URL)
   - Redirect URLs: `http://localhost:3000/**`, `https://<vercel-domain>/**`
4. **Project Settings → API:** copy
   - Project URL → `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`
   - Publishable / anon key → `SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - Secret / service_role → `SUPABASE_SERVICE_ROLE_KEY` (backend only)
   - JWT Secret → `SUPABASE_JWT_SECRET` (optional if using JWKS)
5. JWKS (recommended):  
   `SUPABASE_JWKS_URL=https://<PROJECT_REF>.supabase.co/auth/v1/.well-known/jwks.json`
6. **Settings → Database:** copy
   - Transaction pooler URI → `DATABASE_URL` (use `postgresql+psycopg://…:6543/…?sslmode=require`)
   - Session pooler or direct → `MIGRATION_DATABASE_URL`
   - Direct `db.<ref>.supabase.co:5432` → `CHECKPOINT_DATABASE_URL`
7. **Storage:** create private bucket `atlas-private-documents`  
   Set `SUPABASE_STORAGE_BUCKET=atlas-private-documents`  
   Add policies so authenticated users can upload/read their workspace paths (FastAPI still enforces authz).

### Run migrations

```powershell
cd backend
uv run alembic upgrade head
```

---

## 2. Amazon Bedrock

1. AWS Console → Bedrock in your region (e.g. `eu-north-1`).
2. Enable/confirm access to:
   - Chat: `amazon.nova-lite-v1:0`
   - Embeddings: `amazon.titan-embed-text-v2:0` (**1024** dims)
3. Create IAM user/role with invoke permissions (see `docs/iam/bedrock-atlas-dev.json`).
4. Set in `backend/.env`:
   - `AWS_REGION`
   - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (or instance role in production)
   - `BEDROCK_CHAT_MODEL_ID`, `BEDROCK_EMBEDDING_MODEL_ID`, `EMBEDDING_DIMENSION=1024`

---

## 3. Pinecone

1. Create serverless index `atlas-rag-index-dev`:
   - Dimension **1024**
   - Metric **cosine**
2. Copy API key → `PINECONE_API_KEY`
3. Copy index host → `PINECONE_INDEX_HOST`
4. Set `PINECONE_INDEX_NAME`, `PINECONE_CLOUD`, `PINECONE_REGION`
5. Namespaces are created automatically as `ws_{workspace_uuid}` by the backend — never from the browser.

---

## 4. LangSmith

1. Create project `atlas-enterprise-ai-dev`.
2. Create API key → `LANGSMITH_API_KEY`
3. Set `LANGSMITH_PROJECT=atlas-enterprise-ai-dev`
4. Local: `LANGSMITH_TRACING=false` until ready; production: `true` with redaction policy (no raw docs/secrets in traces).

---

## 5. Stripe (test mode first)

1. Create product **Atlas Pro**, recurring **$49/month**.
2. Copy Price ID → `STRIPE_PRICE_ID`
3. Copy Secret key → `STRIPE_SECRET_KEY`
4. Publishable key → `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` / `STRIPE_PUBLISHABLE_KEY`
5. After API is deployed, add webhook endpoint:  
   `https://<API_HOST>/api/v1/webhooks/stripe`  
   Events: `checkout.session.completed`, `customer.subscription.*`, `invoice.paid`, `invoice.payment_failed`
6. Webhook signing secret → `STRIPE_WEBHOOK_SECRET`

Plans (enforced in FastAPI):

| | Free | Pro |
|---|---|---|
| Members | 3 | 25 |
| Docs | 20 | 500 |
| File size | 10 MiB | 25 MiB |
| Storage | 500 MiB | 20 GiB |
| Chats/month | 100 | 5,000 |
| Custom prompt | No | Yes |

Over limit → block **new uploads + new chat**.

---

## 6. Verify env (no secrets printed)

```powershell
cd backend
uv run python scripts/verify_env.py
uv run pytest
```

```powershell
cd frontend
bun run lint
bun run typecheck
```

---

## 7. Run locally

Fill `backend/.env` and `frontend/.env.local` first (sections 1–5).  
`NEXT_PUBLIC_API_BASE_URL` must be `http://127.0.0.1:8000/api/v1`.

Apply schema:

```powershell
cd backend
uv run alembic upgrade head
```

Terminal A — API:

```powershell
cd backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal B — ingestion worker (keep running):

```powershell
cd backend
uv run python scripts/run_ingestion_worker.py
# optional: uv run python scripts/run_ingestion_worker.py --once
```

Terminal C — web:

```powershell
cd frontend
bun run dev
```

Open:

- App: http://localhost:3000  
- API docs: http://127.0.0.1:8000/docs  
- Live: http://127.0.0.1:8000/health/live  
- Ready: http://127.0.0.1:8000/health/ready  

Optional local Stripe webhooks:

```powershell
stripe listen --forward-to http://127.0.0.1:8000/api/v1/webhooks/stripe
```

Copy the CLI webhook secret into `STRIPE_WEBHOOK_SECRET`.

---

## 8. Smoke test checklist

1. Sign up → becomes **Owner** (org + workspace auto-created).
2. Owner invites a Member (email).
3. Upload a small PDF/TXT → status reaches `ready`.
4. Ask a question in Chat → grounded answer + citations.
5. Ask a follow-up → uses conversation context.
6. Member can delete **own** doc only; Owner can delete any.
7. Hit Free chat/upload limits → API blocks with clear error.
8. Owner opens Billing → Stripe Checkout (test card `4242…`).
9. Webhook updates subscription → Pro entitlements apply.
10. Owner sets workspace system prompt (Pro) → answers reflect it; safety layer still locked.

---

## 9. Deploy backend (FastAPI Cloud)

1. Install/login FastAPI Cloud CLI.
2. Deploy from `backend/`.
3. Set **all** server secrets (Supabase, DB, AWS, Pinecone, LangSmith, Stripe) in the Cloud dashboard — never `NEXT_PUBLIC_*` secrets.
4. Run migrations against production DB (direct URL):  
   `uv run alembic upgrade head`
5. Confirm `/health/live` and `/health/ready`.
6. Point Stripe webhook at production API URL.

---

## 10. Deploy frontend (Vercel)

1. Import repo; root `frontend/`; install command `bun install`; build `bun run build`.
2. Env: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_BASE_URL`, optional Stripe publishable.
3. Add Vercel URL to Supabase Auth redirect allow-list.
4. Add Vercel origin to backend `CORS_ORIGINS`.

---

## 11. Production go-live extras

- Separate Supabase / Pinecone / LangSmith / Stripe **live** projects/keys
- Pinecone index `atlas-rag-index-prod` (still 1024 / cosine)
- Rotate any keys that were ever pasted into chat
- Confirm Storage bucket private + RLS policies
- Confirm LangSmith redaction
- Backup/retention plan for Postgres + Storage

---

## 12. Common failures

| Symptom | Fix |
|---|---|
| DB connect error | Wrong pooler vs direct URL; URL-encode password; `sslmode=require` |
| 401 from API | Missing/expired Supabase access token; JWT secret/JWKS mismatch |
| Upload fails | Bucket name/policies; file > plan limit |
| Empty RAG answers | Ingestion not `ready`; wrong Pinecone host/dim; Bedrock access |
| Stripe still Free after pay | Webhook secret/URL wrong; check `stripe_webhook_events` |

---

## Reference docs

| Doc | Role |
|---|---|
| `docs/requirements.md` | Product rules |
| `docs/architecture.md` | ADRs |
| `docs/environments.md` | Naming |
| `docs/supabase-migration.md` | Appwrite → Supabase |
| `docs/stripe/products.md` | Billing product |
| `docs/ATLAS_Implementation_Plan.md` | Phase roadmap |

When this checklist is done, Atlas is ready for end-to-end use.
