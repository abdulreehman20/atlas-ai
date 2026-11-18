<div align="center">

# 🛰️ Atlas Enterprise AI

### Grounded enterprise knowledge copilot for your private documents

[![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=for-the-badge&logo=supabase&logoColor=black)](https://supabase.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-000000?style=for-the-badge&logo=databricks&logoColor=white)](https://www.pinecone.io/)
[![Stripe](https://img.shields.io/badge/Stripe-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://stripe.com/)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/)

<br />

**Ask questions. Get cited answers. Stay inside your workspace.**

[Features](#-features) · [Problem](#-the-problem) · [Tech Stack](#-tech-stack) · [Installation](#-installation) · [Docs](#-documentation)

</div>

---

## ✨ Overview

**Atlas Enterprise AI** is a multi-tenant RAG (Retrieval-Augmented Generation) platform that lets teams upload private documents and chat with an AI assistant that answers **only from their evidence** — with citations, plan limits, billing, and human-in-the-loop approvals.

It is built as a monorepo:

| Area | Stack |
|------|--------|
| `frontend/` | Next.js · React · Bun · shadcn/ui |
| `backend/` | FastAPI · SQLModel · LangChain · Python worker |
| `docs/` | Architecture, env, and API testing guides |

---

## 🎯 The Problem

Enterprise teams drown in PDFs, policies, and internal notes — but generic chatbots:

- ❌ Invent answers when documents are missing  
- ❌ Mix data across customers / workspaces  
- ❌ Skip citations and audit trails  
- ❌ Have no plan limits, billing, or approval gates  

**Atlas solves this** by grounding every answer in workspace documents, enforcing tenancy on the server, and pairing chat with real product controls (members, uploads, Stripe Pro, HITL approvals).

---

## 🚀 Features

- 📄 **Document ingestion** — PDF, TXT, MD, DOCX, HTML → chunk → embed → Pinecone  
- 💬 **Grounded chat** — answers with document citations  
- 🏢 **Workspaces & roles** — owner / member, invites, memberships  
- 🔐 **Supabase Auth** — JWT verified on every API call  
- 💳 **Stripe billing** — Free vs Pro entitlements via webhooks  
- ✅ **HITL approvals** — sensitive tools pause for owner decision  
- 🌙 **Dark / light UI** — modern settings, documents, members, chat  

---

## 🧩 Tech Stack

<div align="center">

| Layer | Technologies |
|:-----:|:-------------|
| **Frontend** | <img src="https://cdn.simpleicons.org/nextdotjs/000000" width="18" height="18" alt="Next.js"/> Next.js · <img src="https://cdn.simpleicons.org/react/61DAFB" width="18" height="18" alt="React"/> React · <img src="https://cdn.simpleicons.org/typescript/3178C6" width="18" height="18" alt="TypeScript"/> TypeScript · <img src="https://cdn.simpleicons.org/tailwindcss/06B6D4" width="18" height="18" alt="Tailwind"/> Tailwind · <img src="https://cdn.simpleicons.org/bun/000000" width="18" height="18" alt="Bun"/> Bun · shadcn/ui |
| **Backend** | <img src="https://cdn.simpleicons.org/fastapi/009688" width="18" height="18" alt="FastAPI"/> FastAPI · <img src="https://cdn.simpleicons.org/python/3776AB" width="18" height="18" alt="Python"/> Python 3.12+ · SQLModel · <img src="https://cdn.simpleicons.org/uv/DE5FE9" width="18" height="18" alt="uv"/> uv |
| **Data** | <img src="https://cdn.simpleicons.org/supabase/3FCF8E" width="18" height="18" alt="Supabase"/> Supabase Auth · Postgres · Storage |
| **AI / RAG** | <img src="https://cdn.simpleicons.org/langchain/1C3C3C" width="18" height="18" alt="LangChain"/> LangChain · OpenRouter · Pinecone |
| **Billing** | <img src="https://cdn.simpleicons.org/stripe/635BFF" width="18" height="18" alt="Stripe"/> Stripe Checkout + webhooks |
| **Ops** | LangSmith · Sentry · Biome |

</div>

```text
User
  └─ Next.js + Supabase Auth
       ├─ Supabase Storage (private uploads)
       └─ FastAPI (JWT Bearer)
            ├─ Supabase PostgreSQL
            ├─ Ingestion worker
            ├─ OpenRouter (chat + embeddings)
            ├─ Pinecone (ws_{workspace_id})
            ├─ LangChain RAG + guardrails
            └─ Stripe webhooks → entitlements
```

---

## 📦 Installation

### Prerequisites

- <img src="https://cdn.simpleicons.org/python/3776AB" width="16" height="16" alt="Python"/> **Python 3.12+** and [uv](https://docs.astral.sh/uv/)
- <img src="https://cdn.simpleicons.org/bun/000000" width="16" height="16" alt="Bun"/> **Bun** (frontend)
- <img src="https://cdn.simpleicons.org/supabase/3FCF8E" width="16" height="16" alt="Supabase"/> Supabase project (Auth, Postgres, Storage)
- OpenRouter API key · Pinecone index · Stripe test keys (optional for billing)

### 1. Clone

```bash
git clone https://github.com/abdulreehman20/atlas-ai.git
cd atlas-ai
```

### 2. Backend

```bash
cd backend
uv sync
cp .env.example .env
# fill SUPABASE_*, DATABASE_URL, OPENROUTER_*, PINECONE_*, STRIPE_* …
```

Run migrations (if configured for your DB), then start the API:

```bash
fastapi dev app/main.py
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Optional ingestion worker:

```bash
uv run python scripts/run_ingestion_worker.py
```

Local Stripe webhooks (billing):

```bash
stripe listen --forward-to localhost:8000/api/v1/billing/webhooks/stripe
# put the printed whsec_… into STRIPE_WEBHOOK_SECRET, then restart the API
```

### 3. Frontend

```bash
cd frontend
cp .env.example .env.local   # if present — set NEXT_PUBLIC_API_BASE_URL + Supabase keys
bun install
bun run dev
```

App: [http://localhost:3000](http://localhost:3000)

### 4. Environment tips

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend URL (e.g. `http://127.0.0.1:8000/api/v1`) |
| `SUPABASE_URL` / keys | Auth, Storage, Postgres |
| `OPENROUTER_API_KEY` | Chat + embeddings |
| `PINECONE_*` | Vector index (dimension must match embeddings, e.g. 2048) |
| `STRIPE_SECRET_KEY` / `STRIPE_PRICE_ID` / `STRIPE_WEBHOOK_SECRET` | Pro billing |

> ⚠️ Never commit `.env` files. Use `.env.example` as the template.

---

## 🧪 Quick checks

```bash
# Backend
cd backend && uv run pytest -q

# Frontend
cd frontend && bun run lint
```

API walkthrough: [`docs/testing/api_testing.md`](docs/testing/api_testing.md)

---

## 📚 Documentation

| Doc | What it covers |
|-----|----------------|
| [`docs/plan/architecture.md`](docs/plan/architecture.md) | Architecture & ADRs |
| [`docs/testing/api_testing.md`](docs/testing/api_testing.md) | Swagger / API testing |
| [`docs/others/environments.md`](docs/others/environments.md) | Environment notes |

---

## 🗺️ Product surface

| Route | Purpose |
|-------|---------|
| `/chat` | Grounded Q&A with citations |
| `/documents` | Upload & processing status |
| `/members` | Invites & membership |
| `/approvals` | HITL review queue (owner) |
| `/settings` | Profile, workspace prompt, billing |

---

<div align="center">

**Built for teams who need answers they can trust.**

🛰️ **Atlas Enterprise AI**

</div>
