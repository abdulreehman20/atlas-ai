# Atlas Enterprise AI — Environments (Supabase stack)

**Updated:** 2026-11-07  
**See also:** `supabase-migration.md`

---

## 1. Environment topology

| Environment | Supabase project (suggested name) | Stripe |
|---|---|---|
| development | `atlas-enterprise-ai-dev` | Test mode |
| production | `atlas-enterprise-ai-prod` | Live mode |

---

## 2. Canonical resource names

| Resource | Development | Production |
|---|---|---|
| Supabase project | `atlas-enterprise-ai-dev` | `atlas-enterprise-ai-prod` |
| Storage bucket | `atlas-private-documents` | `atlas-private-documents` |
| Pinecone index | `atlas-rag-index-dev` | `atlas-rag-index-prod` |
| LangSmith project | `atlas-enterprise-ai-dev` | `atlas-enterprise-ai-prod` |
| Stripe product | `Atlas Pro` (test) | `Atlas Pro` (live) |
| Ingestion worker | `atlas-ingestion-worker` | `atlas-ingestion-worker` |

---

## 3. Region / model decisions

| Setting | v1 decision |
|---|---|
| Supabase region | Choose once (e.g. closest to users); record below |
| Bedrock chat | `amazon.nova-lite-v1:0` |
| Bedrock embedding | `amazon.titan-embed-text-v2:0` @ **1024** dims |
| Pinecone | dense serverless, cosine, dim 1024 |
| Namespace | `ws_{workspace_uuid}` |

### Operator fill-in

| Field | Value |
|---|---|
| Supabase project URL | |
| Supabase region | |
| AWS region | |
| Pinecone region / host | |

---

## 4. Supabase PostgreSQL URLs

From Supabase **Project Settings → Database**:

| Env var | Source | Use |
|---|---|---|
| `DATABASE_URL` | Pooler (Transaction) URI, SQLAlchemy form `postgresql+psycopg://...` | FastAPI runtime |
| `MIGRATION_DATABASE_URL` | Direct connection URI (`postgresql+psycopg://...`) | Alembic |
| `CHECKPOINT_DATABASE_URL` | Direct connection URI (`postgresql://...`) | LangChain checkpointer |

Always use TLS (`sslmode=require` where applicable). URL-encode special characters in passwords.

---

## 5. Supabase Auth & Storage

| Setting | v1 |
|---|---|
| Auth | Email / password enabled |
| Site URL (local) | `http://localhost:3000` |
| Redirect URLs | `http://localhost:3000/**` (+ Vercel URLs later) |
| Bucket | `atlas-private-documents`, **private** |
| Allowed MIME | pdf, txt, md, docx, html |
| Max object size | 25 MiB (API enforces plan limits) |

---

## 6. Backend env inventory (`SUPABASE_*`)

```dotenv
SUPABASE_URL=https://<PROJECT_REF>.supabase.co
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
SUPABASE_STORAGE_BUCKET=atlas-private-documents
```

Frontend:

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://<PROJECT_REF>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Never put service role or JWT secret in `NEXT_PUBLIC_*`.

---

## 7. Provisioning checklist

### Supabase

- [ ] Create project `atlas-enterprise-ai-dev`
- [ ] Enable email/password Auth; set Site URL + redirects
- [ ] Copy Project URL, anon key, service role key, JWT secret
- [ ] Copy Database pooler + direct URLs into `backend/.env`
- [ ] Create private Storage bucket `atlas-private-documents`
- [ ] Configure Storage policies (authenticated upload/read per product rules — enforced again in FastAPI)

### Bedrock / Pinecone / LangSmith / Stripe

- [ ] Same as before (see prior Phase 2 checklist) — unchanged by this migration

### Local

- [ ] Fill `backend/.env` and `frontend/.env.local`
- [ ] `uv run python scripts/verify_env.py`
