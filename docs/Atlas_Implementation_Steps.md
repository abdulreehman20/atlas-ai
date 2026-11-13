# Atlas Enterprise AI — Complete Setup, Testing & Deployment Guide

> **TECHNOLOGY AMENDMENT (2026-11-07):** Former Appwrite Auth/Database/Storage/Functions requirements are **replaced by Supabase Auth + Supabase PostgreSQL + Supabase Storage**, plus a **Python ingestion worker**. See `docs/supabase-migration.md`. Prefer that document, `requirements.md`, `architecture.md`, and `environments.md` for current stack truth.

---

## 1. Project Stack and Architecture Decisions

This guide replaces the original Conda, AWS S3, Render PostgreSQL, GlassFlow Rius, and legacy setup steps with the selected Atlas stack.

| Area | Selected technology | Responsibility |
|---|---|---|
| Backend runtime | Python 3.12+ | Application runtime and AI services |
| Python environment / package manager | `uv` | Virtual environment, dependency resolution, lockfile, and commands |
| Backend API | FastAPI | REST endpoints, authentication, ingestion coordination, chat, approvals, billing webhooks, and health checks |
| ORM / schemas | SQLModel | Typed relational models and database access |
| Relational database | Supabase PostgreSQL (native PostgreSQL) | Application records, chat history, memory, document metadata, approvals, audit events, and subscriptions |
| Authentication | Supabase Auth | User registration, login, sessions, and identity |
| Authentication integration | Supabase Auth helpers (@supabase/ssr / @supabase/supabase-js) | Next.js client/server auth state and SSR session handling |
| File storage | Supabase Storage | Private uploaded source documents |
| Frontend | Next.js App Router + TypeScript | Web application and dashboard |
| UI | shadcn/ui | Reusable accessible interface components and auth forms |
| AI orchestration | LangChain | Retrieval, prompt construction, model calls, tools, and response composition |
| Conversation memory | LangChain short-term memory + PostgreSQL checkpointer, with SQLModel transcript records | Durable thread state, conversation history, and optional long-term user memory |
| Human approval | LangChain `HumanInTheLoopMiddleware` + persistent PostgreSQL checkpointer + FastAPI approval dashboard | Pause sensitive tool calls until an authorized person approves, edits, or rejects them |
| Context engineering | LangChain prompts, retrieval, message trimming, and metadata | Control what context enters each model call |
| LLM provider | Amazon Bedrock | Chat completion and embedding model APIs |
| Embeddings | Amazon Titan Text Embeddings V2 (initial default) | Create vectors for document chunks and retrieval queries |
| Vector database | Pinecone | Store and retrieve document vectors using tenant/workspace namespaces |
| Observability | LangSmith | Trace and inspect chains, retrieval, model calls, and latency |
| Guardrails | LangChain middleware / application validation | Input, tool, and output safety checks |
| Payments | Stripe | Checkout, subscriptions, and payment lifecycle events |
| Backend deployment | FastAPI Cloud | HTTPS-hosted FastAPI API |
| Frontend deployment | Vercel | Next.js production and preview deployments |

### Important database decision: Supabase PostgreSQL, not TablesDB

This guide assumes that **Supabase PostgreSQL (Native databases → PostgreSQL)** is the relational database. It exposes a normal PostgreSQL connection, so SQLModel, SQLAlchemy, Psycopg, and Alembic can connect directly.

Do **not** select TablesDB (rejected) for the SQLModel connection. TablesDB is accessed through the Supabase API/SDK; it is not a PostgreSQL connection endpoint and SQLModel/Alembic cannot manage its schema directly. If you specifically want TablesDB instead, the persistence layer needs a different implementation and this SQLModel setup must be changed. Supabase PostgreSQL is a separately provisioned database product with its own compute/billing requirements; confirm that your Supabase organization and plan can create it before committing to this architecture.

### Important payment decision: Stripe is the payment processor

Use Stripe Checkout and Stripe webhooks for payment processing. Supabase Auth identifies the user; FastAPI creates Checkout Sessions, receives and verifies Stripe webhook events, and updates subscription state in Supabase PostgreSQL. Supabase has an official Stripe + the Python ingestion worker tutorial, but this deployment uses FastAPI Cloud as the single application backend, so the webhook endpoint lives in FastAPI rather than a separate Python ingestion worker.

### Important memory and HITL decision

Use LangChain's current agent API (`create_agent`) for agent-facing memory and tool workflows. Persist short-term agent state with a PostgreSQL checkpointer; persist the user-visible chat transcript and application-level memory records in SQLModel tables. Use LangChain's `HumanInTheLoopMiddleware` for tool calls that require a human decision. The middleware needs a persistent checkpointer so paused calls can safely resume.

The `langgraph-checkpoint-postgres` package is included only as the PostgreSQL persistence adapter required by LangChain's current agent memory/HITL implementation. This guide does not ask you to author custom LangGraph workflows. Do not use `InMemorySaver` in production: FastAPI Cloud can run multiple instances, and process memory is not shared or durable. Keep long-term user memories separate from thread history, scoped to a verified user/workspace, and subject to an explicit retention/deletion policy.

---

## 2. Prerequisites

Install or create accounts for:

- Python 3.12 or newer.
- `uv` (Python project and environment manager).
- Node.js LTS and `bun`.
- Git and a GitHub repository.
- Supabase project.
- AWS account with Amazon Bedrock model access.
- Pinecone account and API key.
- LangSmith account and API key.
- Stripe account (start in test mode).
- FastAPI Cloud account.
- Vercel account connected to your Git provider.

Useful local checks:

```powershell
python --version
uv --version
node --version
bun --version
git --version
```

Use `uv` for all Python dependency and environment commands. Do not create or activate a Conda environment for this project.

---

## 3. Prepare the Repository

The commands below assume a monorepo with separate backend and frontend applications:

```text
ATLAS-Enterprise-AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── ai/
│   │   └── main.py
│   ├── migrations/
│   ├── scripts/
│   ├── tests/
│   ├── .env.example
│   ├── pyproject.toml
│   ├── uv.lock
│   └── .python-version
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   ├── public/
│   ├── .env.example
│   ├── package.json
│   └── bun-lock.yaml
├── docs/
└── README.md
```

If your repository already has a different structure, keep the existing structure and adjust the paths in the commands below. Do not duplicate an existing project or overwrite its configuration just to match this example.

---

## 4. Create the Python Environment with `uv`

Open PowerShell in the repository root:

```powershell
cd backend
```

If the backend does not already have a `pyproject.toml`, initialize it:

```powershell
uv init --python 3.12
uv python pin 3.12
```

If `pyproject.toml` already exists, skip `uv init`; pin the intended Python version if needed.

Install the backend dependencies:

```powershell
uv add "fastapi[standard]" sqlmodel "psycopg[binary]" alembic pydantic-settings python-dotenv supabase boto3 langchain langchain-aws langchain-pinecone langchain-text-splitters langgraph-checkpoint-postgres langsmith pypdf pymupdf python-docx beautifulsoup4 lxml python-multipart stripe httpx tenacity
```

Install development and testing tools:

```powershell
uv add --dev pytest pytest-asyncio pytest-cov respx ruff
```

Synchronize the environment:

```powershell
uv sync
```

`uv` creates and manages the project `.venv` and `uv.lock`. Commit `pyproject.toml` and `uv.lock` to Git. Do not commit `.venv`.

Run Python commands through `uv run`; activating the environment manually is optional:

```powershell
uv run python --version
uv run fastapi --help
```

For an existing initialized backend, the normal setup command is simply:

```powershell
uv sync
```

---

## 5. Configure Supabase Project, Authentication, and Storage

### 5.1 Create the Supabase project

1. Sign in to the [Supabase Dashboard](https://supabase.co/).
2. Create a project for Atlas Enterprise AI.
3. Choose the project region based on your users, data residency needs, and the services you plan to use. The native PostgreSQL database uses the region of its owning Supabase project.
4. Open **Overview → Add platform → Web app**.
5. Add `localhost` as a hostname for local development.
6. Later, add the Vercel production hostname and the preview hostnames you intend to use.

Supabase Auth checks registered web platforms for browser-origin access. A missing production hostname commonly causes CORS or platform-origin errors.

### 5.2 Configure Supabase Authentication

1. Open **Auth** in the Supabase Dashboard.
2. Enable the sign-in methods your application will support, initially email/password.
3. Configure email verification, password policy, session behavior, and optional OAuth providers according to the product requirements.
4. Use the Supabase Auth helpers (@supabase/ssr / @supabase/supabase-js) in Next.js for sign-in, sign-up, sign-out, current-user state, and SSR session handling.
5. Use shadcn/ui to build the actual sign-in and registration forms. The React library supplies authentication integration and hooks; it is not a replacement for your product's visual UI.

For the Supabase Auth helpers (@supabase/ssr / @supabase/supabase-js)'s Next.js SSR integration, create a server-side API key in **Overview → Integrations → API keys** with the scopes required by the official Next.js quick start (`users.read`, `users.write`, and `sessions.write`). Store this key as a server-only environment variable. Never prefix it with `NEXT_PUBLIC_`, expose it to browser JavaScript, or commit it to Git.

### 5.3 Authenticate FastAPI requests with Supabase access tokens

Use this request flow:

1. The user signs in through Supabase Auth in Next.js.
2. Before calling a protected FastAPI endpoint, the frontend obtains a short-lived Supabase access token using the authenticated account's `createJWT()` operation.
3. The frontend sends the token to FastAPI in an `Authorization: Bearer <jwt>` header (or in a dedicated header if your API contract specifies one).
4. FastAPI creates a request-scoped Supabase server client client, attaches the user JWT, and validates the identity through the Supabase Account API.
5. FastAPI extracts the verified Supabase user ID and resolves the user's workspace/tenant membership from the relational database.
6. The API authorizes the requested operation against that membership and resource ownership.

Supabase access token is short-lived (15 minutes by default). Generate a fresh JWT when needed; do not treat it as a permanent API key. Create a fresh request-scoped Supabase client / JWT verification for user-scoped calls. Do not use an unrestricted project API key as a substitute for verifying the requesting user.

Use an Supabase project API key only for background/admin operations that genuinely require server privileges. Give it minimum scopes and keep it exclusively in FastAPI Cloud secrets.

### 5.4 Create a private Supabase Storage bucket

1. In the Supabase project, open **Storage** and create a bucket such as `atlas-private-documents`.
2. Keep the bucket private; do not grant public read access.
3. Enable file-level security where available and define who can create, read, update, and delete files.
4. Grant access to the file owner or the intended workspace members only.
5. Configure a maximum file size and allowed file extensions/MIME types consistent with the application policy.
6. Enable the bucket's available encryption/security options.
7. Test upload, download, and delete operations with a normal user session—not only an administrative API key.

Recommended initial file policy (adjust only when the implementation supports the formats): PDF, TXT, Markdown, DOCX, and HTML; maximum 25 MiB per file. Validate file size, type, and content again on the backend. Frontend accept filters are not security controls.

### 5.5 Document upload flow

Use Supabase Storage for the original file bytes and PostgreSQL for document metadata:

1. Next.js obtains the authenticated user context.
2. The browser uploads the file to the private Supabase Storage bucket using the authenticated Supabase session and correct file permissions.
3. The frontend sends the resulting Supabase Storage object ID to FastAPI with its Supabase access token.
4. FastAPI verifies the user, workspace membership, file ownership/permission, content type, file size, and current document state.
5. FastAPI creates or updates the document metadata record and dispatches ingestion.
6. The ingestion pipeline downloads the file from Supabase Storage using a user-scoped JWT or a narrowly scoped server credential, extracts text, chunks it, embeds it, and indexes it in the appropriate Pinecone namespace.
7. The API updates the document's processing status and reports the final state to the UI.

Do not store uploaded PDF/DOCX bytes inside PostgreSQL rows. Store file IDs and metadata in PostgreSQL; store the original binary in Supabase Storage; store embeddings and retrieval metadata in Pinecone.

---

## 6. Create Supabase PostgreSQL

This is the relational database used by SQLModel and Alembic.

1. In the Supabase Dashboard, open your project and select **Databases**.
2. Choose **Create database**.
3. Under database type, select **PostgreSQL** from **Native databases** (not TablesDB).
4. Choose a database name, such as `atlas-enterprise-ai`.
5. Select a compute specification appropriate for development or production.
6. Create the database and wait until its status is `ready`.
7. Open the database's **Credentials** panel and copy the connection details securely.
8. Use TLS (`sslmode=require`).

### Runtime connection versus migration connection

Supabase provides a pooled connection endpoint for normal application traffic and a direct PostgreSQL endpoint. Use the pooler for the FastAPI runtime where supported, and use the direct endpoint for schema migrations that require a stable session.

- **Runtime:** pooler port `6432`.
- **Migrations/admin:** direct PostgreSQL port `5432`.

Adapt the connection string copied from the Console to the Psycopg SQLAlchemy driver form. Example structure only:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:6432/DATABASE?sslmode=require
MIGRATION_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
```

Use the actual host, username, database name, and password from your Supabase database. URL-encode reserved characters in the password. Do not copy the example values literally.

### SQLModel and Alembic

1. Configure SQLModel's engine from `DATABASE_URL`.
2. Configure Alembic to load the SQLModel metadata from your model modules.
3. Use Alembic migrations for all schema changes.
4. Use `MIGRATION_DATABASE_URL` for migration commands when configured.
5. Do not create tables with `SQLModel.metadata.create_all()` at production startup.

Suggested relational entities for the Atlas feature set:

- `workspaces` and `workspace_memberships`
- `documents` and `ingestion_jobs`
- `chat_sessions` and `chat_messages`
- `user_memories` (only for explicitly approved memory use cases)
- `approvals` (the dashboard-facing approval record and audit state)
- `feedback`
- `audit_events`
- `subscriptions` and `stripe_events`

LangChain's PostgreSQL checkpointer maintains its own checkpoint tables. Initialize those tables through the checkpointer's setup operation once as a controlled setup/release step, not on every API request. Use a server-controlled `thread_id` derived from a conversation that has already been authorized for the current user/workspace. Do not allow a caller to read or resume another tenant's checkpoint by supplying an arbitrary thread ID.

Store Supabase user IDs as external identity references. The backend must still enforce workspace and document ownership on every query and mutation.

If Alembic has not been initialized in the backend yet:

```powershell
uv run alembic init migrations
```

After configuring `alembic.ini` / `migrations/env.py` to read the correct database URL and SQLModel metadata, create and apply the first migration:

```powershell
uv run alembic revision --autogenerate -m "create initial atlas schema"
uv run alembic upgrade head
uv run alembic current
```

Review generated migration files before applying them. Autogeneration is a starting point, not a substitute for checking constraints, indexes, foreign keys, and nullability.

### LangChain persistent memory / HITL checkpointer

Because this project uses LangChain's current `create_agent` memory and `HumanInTheLoopMiddleware`, install the PostgreSQL checkpointer adapter (already included in the dependency command in Section 4). Configure `CHECKPOINT_DATABASE_URL` with the Supabase PostgreSQL direct connection (port `5432`) and initialize the checkpointer schema once from a controlled setup script or release command. The LangChain documentation demonstrates this with `PostgresSaver.from_conn_string(...)` followed by `checkpointer.setup()`. Keep the saver lifecycle managed by the application lifespan/connection-pool strategy; do not open a new persistent pool for every request.

The SQLModel `chat_messages` table remains the application's transcript and UI source of truth. The checkpointer stores the agent's resumable execution state, including paused HITL operations. These serve different purposes and should not be treated as interchangeable.

---

## 7. Configure Amazon Bedrock

The original guide used Amazon Nova Lite for chat and Titan Text Embeddings V2 for embeddings. This guide keeps those as the initial defaults; change them only after verifying model access, cost, latency, and region availability for your AWS account.

### 7.1 Enable model access

1. Sign in to the [AWS Console](https://console.aws.amazon.com/).
2. Open **Amazon Bedrock** in the AWS region you intend to use.
3. Confirm that the selected account and region can invoke the chosen foundation models.
4. Start with:
   - Chat model: `amazon.nova-lite-v1:0`
   - Embedding model: `amazon.titan-embed-text-v2:0`
5. Confirm the embedding request is configured to return **1024 dimensions**. The Pinecone index dimension must exactly match the embedding output dimension.

Model availability, access requirements, model IDs, and cross-region inference behavior can differ by AWS region and account. Verify these settings in the Bedrock console before creating the production index.

### 7.2 Create restricted AWS credentials

Create a dedicated IAM identity for Atlas rather than using the AWS root account. Grant only the Bedrock invocation permissions needed for the selected models and region. Do not grant S3 permissions because Supabase Storage replaces S3 in this architecture.

For local development, use your normal AWS credential provider chain or an AWS profile where practical. For FastAPI Cloud, provide the minimum required AWS credentials as encrypted secrets (or use a supported short-lived credential mechanism). Never put AWS credentials in Next.js `NEXT_PUBLIC_*` variables.

### 7.3 Bedrock test

After the backend environment variables are set, run a small integration test that:

1. Instantiates the LangChain Bedrock chat model.
2. Invokes it with a non-sensitive test prompt.
3. Instantiates the Bedrock embedding model.
4. Embeds a short test string and verifies that the returned vector length equals `EMBEDDING_DIMENSION` (1024 in this setup).

Keep document content and real customer data out of setup tests.

---

## 8. Configure Pinecone

1. Open the [Pinecone Console](https://app.pinecone.io/).
2. Create a project and an API key.
3. Create a **dense** serverless index named `atlas-rag-index` (or your chosen name).
4. Set the dimension to `1024` to match the selected Titan embedding configuration.
5. Set the similarity metric to `cosine`.
6. Select a supported cloud and region based on availability, latency, data residency, and cost.
7. Wait until the index reports ready.
8. Copy the index host if your LangChain/Pinecone client configuration uses it.

You can create the index from the Pinecone Console or from a controlled provisioning script. Do not make API startup responsible for racing to create the same index across multiple FastAPI Cloud instances. Index creation should be an explicit setup/provisioning step.

### Namespace strategy

Use one namespace per tenant/workspace, for example:

```text
workspace_<internal_workspace_id>
```

The backend derives this namespace only after authenticating the user and resolving their workspace membership. Never accept an unrestricted Pinecone namespace from the browser.

Store metadata such as `workspace_id`, `document_id`, `chunk_id`, `owner_user_id`, `visibility`, and `source_type` with vectors where appropriate. Apply metadata filters to every retrieval request as an additional authorization boundary. A namespace is a data partition, not a replacement for authentication, authorization, or ownership checks.

Keep the same embedding model and dimension for both document ingestion and query embedding. If you change the embedding model or dimensions, create a compatible index and re-embed/reindex the existing corpus rather than mixing incompatible vector spaces.

---

## 9. Configure LangSmith Observability

1. Create or sign in to [LangSmith](https://smith.langchain.com/).
2. Create a project named `atlas-enterprise-ai`.
3. Create an API key for the application.
4. Add the tracing environment variables to local backend configuration and FastAPI Cloud secrets.

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=YOUR_LANGSMITH_API_KEY
LANGSMITH_PROJECT=atlas-enterprise-ai
```

Instrument and review traces for:

- Document extraction and chunking stages.
- Embedding requests.
- Pinecone upsert and retrieval operations.
- Context assembly and prompt construction.
- Bedrock model calls.
- Tool execution and approval handoffs.
- Response validation and guardrails.

### Sensitive-data policy for traces

Tracing is not permission to export private enterprise content. Before enabling production tracing, decide which inputs, outputs, metadata, and errors may be captured. Redact or omit document text, credentials, tokens, personal information, and sensitive user prompts by default. Use synthetic test data when validating the tracing pipeline. Restrict LangSmith project access and set an appropriate data-retention policy.

---

### 9.1 Configure LangChain, memory, context engineering, and guardrails

This project uses LangChain as the agent/model interface. Build the model adapters with `langchain-aws` (`ChatBedrockConverse` for chat and `BedrockEmbeddings` for vectors) and the Pinecone integration package (`langchain-pinecone`). Keep the model IDs and region in settings rather than hardcoding them inside route handlers.

#### Short-term conversation memory

- Use LangChain's agent state/checkpointer for resumable thread state, including any agent execution paused for approval.
- Use a persistent PostgreSQL checkpointer in production; do not use `InMemorySaver` outside local tests.
- Keep the end-user chat transcript in SQLModel `chat_messages` so the UI can list, paginate, export, and audit conversation history independently of agent execution state.
- Derive the LangChain `thread_id` on the backend from a conversation that has already been authorized for the current user and workspace.
- Trim or summarize older turns before model calls so stale messages do not consume the entire context window.

#### Long-term memory

Use a separate SQLModel `user_memories` (or `workspace_memories`) table for durable facts that the product intentionally saves. Retrieve only memories belonging to the authenticated user/workspace. Give users a way to inspect and delete saved memories. Do not automatically turn every conversation message into permanent memory.

#### Context engineering for RAG

Build every model request from bounded, purpose-specific context:

1. **System policy:** Atlas role, response rules, tenant boundary, source-grounding requirements, and tool policy.
2. **Current request:** the latest user question and any required validated parameters.
3. **Conversation context:** only the recent/relevant turns from the authorized thread; rephrase a follow-up question when needed for retrieval.
4. **Retrieved evidence:** top relevant chunks from the authenticated workspace's Pinecone namespace, with document ID, title, page/section, and chunk reference.
5. **Optional saved memory:** only relevant, permitted user/workspace memories.
6. **Tool results:** only the minimum fields needed for the next reasoning step.

Set a token budget for history and retrieved evidence. Prefer a small set of high-relevance chunks over sending entire documents. Keep retrieved document content clearly separated from system instructions and treat it as untrusted data. Require the answer to cite the available source references; when the evidence is insufficient, the assistant should say so rather than inventing an answer.

#### Guardrails

Apply checks at multiple layers; do not rely on a system prompt or regex alone:

- **API boundary:** Pydantic request validation, upload validation, rate limits, authorization, workspace/document ownership, and server-side quotas.
- **Input and context:** detect/handle sensitive data where required, treat document text as untrusted, defend against prompt injection, and prevent secrets from being added to model context.
- **Tool boundary:** expose only allowlisted tools; validate tool arguments; re-check authorization inside every tool; impose tool-call limits; make side-effecting operations idempotent.
- **Human approval:** attach LangChain `HumanInTheLoopMiddleware` to tools such as document deletion or policy changes. Configure safe actions separately from actions that require approval. A paused call must not execute until an authorized person approves it.
- **Output boundary:** validate structured output with Pydantic or an equivalent schema, apply application policy checks, and ensure sources/permissions are valid before returning the response.
- **Observability:** redact secrets and sensitive content before sending traces to LangSmith.

LangChain's middleware catalog includes human approval, PII handling, summarization, model/tool call limits, retries, and custom middleware. Use those as agent-level controls, while keeping authentication, tenant authorization, payment entitlement, and database constraints in deterministic backend code.

---

## 10. Configure Stripe Payments

Use Stripe in **test mode** first.

1. Create or sign in to your [Stripe account](https://dashboard.stripe.com/).
2. Open **Product catalogue** and create the subscription products/plans Atlas will sell.
3. Create recurring or one-time prices as required by the product.
4. Copy the relevant Price IDs (for example, `price_...`).
5. Copy the test Secret key from **Developers → API keys**.
6. After FastAPI Cloud is deployed, create a Stripe webhook endpoint pointing to the production API, for example:

```text
https://<YOUR_FASTAPI_CLOUD_DOMAIN>/api/v1/billing/webhooks/stripe
```

7. Subscribe to the events used by your implementation. A typical subscription integration needs events such as:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
   - `invoice.payment_failed`

8. Copy the webhook signing secret and store it as `STRIPE_WEBHOOK_SECRET`.

### Payment flow

1. An authenticated user requests a plan change or checkout from Next.js.
2. FastAPI verifies the Supabase access token and resolves the current user's internal workspace/account.
3. FastAPI creates a Stripe Checkout Session using server-side Stripe credentials and the server-configured Price ID.
4. The user completes checkout on Stripe-hosted checkout.
5. Stripe sends an event to the FastAPI webhook endpoint.
6. FastAPI verifies the webhook signature against the **raw request body**, records the event ID for idempotency, and updates the subscription record.
7. The application reads subscription status from PostgreSQL to authorize plan-specific features.

Do not grant paid access based only on a browser redirect or a frontend success page. The verified webhook event is the source of truth. Make event handling idempotent so Stripe retries cannot create duplicate subscription changes. Never store or log raw card details.

If your product only needs a checkout redirect, a publishable key may not be required in the browser. Add a Stripe publishable key to the frontend only if your chosen Stripe.js flow actually uses it.

---

## 11. Configure Backend Environment Variables

Create `backend/.env.example` and copy it to `backend/.env` for local development.

PowerShell:

```powershell
Copy-Item .env.example .env
```

Example backend environment template (replace every placeholder with your own value):

```dotenv
# Application
APP_ENV=development
APP_NAME=Atlas Enterprise AI
API_V1_PREFIX=/api/v1
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
HITL_ENABLED=true
MEMORY_MAX_TURNS=6
RAG_TOP_K=5
CONTEXT_TOKEN_BUDGET=12000
PROMPT_VERSION=atlas-rag-v1
UPLOAD_MAX_FILE_SIZE_MB=25

# Supabase project (user JWTs are request-scoped)
SUPABASE_URL=https://<REGION>.supabase.co/v1
SUPABASE_ANON_KEY=<SUPABASE_ANON_KEY>
SUPABASE_STORAGE_BUCKET=<PRIVATE_BUCKET_ID>
# Optional, only for narrowly scoped server-side admin/background operations
SUPABASE_SERVICE_ROLE_KEY=<SERVER_ONLY_SUPABASE_SERVICE_ROLE_KEY>

# Supabase PostgreSQL
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:6432/DATABASE?sslmode=require
MIGRATION_DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
CHECKPOINT_DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require

# AWS / Amazon Bedrock
AWS_REGION=<BEDROCK_REGION>
AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID>
AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY>
BEDROCK_CHAT_MODEL_ID=amazon.nova-lite-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
EMBEDDING_DIMENSION=1024

# Pinecone
PINECONE_API_KEY=<PINECONE_API_KEY>
PINECONE_INDEX_NAME=atlas-rag-index
PINECONE_INDEX_HOST=<PINECONE_INDEX_HOST>
PINECONE_CLOUD=aws
PINECONE_REGION=<PINECONE_REGION>

# LangSmith
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<LANGSMITH_API_KEY>
LANGSMITH_PROJECT=atlas-enterprise-ai

# Stripe (test keys locally; production keys only in production secrets)
STRIPE_SECRET_KEY=<STRIPE_SECRET_KEY>
STRIPE_WEBHOOK_SECRET=<STRIPE_WEBHOOK_SIGNING_SECRET>
STRIPE_PRICE_ID=<STRIPE_PRICE_ID>
```

Notes:

- `SUPABASE_SERVICE_ROLE_KEY` is optional. Prefer user JWT authentication for user-scoped Supabase operations. Add a server API key only for operations that require project-level privileges.
- `DATABASE_URL` and `MIGRATION_DATABASE_URL` are examples of driver-formatted URLs. Use the exact credentials from the Supabase database Console and encode reserved characters in passwords.
- `PINECONE_INDEX_HOST` may be optional depending on the Pinecone client version/configuration. If the client needs a host, copy the exact host from the Pinecone Console.
- If your AWS runtime uses a different credential provider, remove the static key variables and configure that provider instead.
- Do not add secrets to source control, screenshots, error responses, or client-side environment variables.

Add these local files and folders to `.gitignore`:

```gitignore
.env
.env.*
!.env.example
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
.coverage
htmlcov/
```

If your project needs a committed non-secret `.env.example`, ensure the ignore rules above do not exclude it.

---

## 12. Configure the Next.js Frontend

If the frontend does not exist yet, create it from the repository root:

```powershell
bun create next-app frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/*"
cd frontend
```

If the Next.js app already exists, run the install commands from its directory instead of creating another app.

Install Supabase's official React library and its Next.js SSR dependencies:

```powershell
bun add @supabase/supabase-js @supabase/ssr @tanstack/react-query
```

Initialize shadcn/ui and add the components used by the application:

```powershell
bun dlx shadcn@latest init
bun dlx shadcn@latest add button card input label form dialog dropdown-menu avatar badge textarea table tabs skeleton alert-dialog
```

Optional form and icon utilities if the project uses them:

```powershell
bun add zod react-hook-form @hookform/resolvers lucide-react
```

Create `frontend/.env.example`, then copy it to `.env.local`:

```powershell
Copy-Item .env.example .env.local
```

Example frontend environment template:

```dotenv
# Public Supabase values; these are safe to expose to the browser
NEXT_PUBLIC_SUPABASE_URL=https://<REGION>.supabase.co/v1
NEXT_PUBLIC_SUPABASE_ANON_KEY=<SUPABASE_ANON_KEY>

# Server-only Supabase key required by the official Next.js SSR handler
# Never prefix this value with NEXT_PUBLIC_
SUPABASE_SERVICE_ROLE_KEY=<SUPABASE_SERVICE_ROLE_KEY>

# FastAPI Cloud API base URL; local development uses localhost
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1

# Only set this if the frontend's selected Stripe.js integration needs it
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=<STRIPE_PUBLISHABLE_KEY>
```

Implement the Supabase JS/SSR provider and the official Next.js SSR handler according to the Supabase Next.js quick start. Keep the Supabase API key in server-only code. Use Supabase's session-aware hooks for current user state and shadcn/ui for the interface.

### Local frontend run

```powershell
bun install
bun dev
```

Open:

```text
http://localhost:3000
```

---

## 13. Run Database Migrations and Start the Backend

From the `backend` directory:

```powershell
uv sync
uv run alembic upgrade head
uv run alembic current
```

Start FastAPI locally:

```powershell
uv run fastapi dev app/main.py --host 127.0.0.1 --port 8000
```

If your project uses a Uvicorn entrypoint instead, the equivalent development command is:

```powershell
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open these local endpoints (adjust the API docs URL if your FastAPI configuration customizes it):

| Purpose | URL |
|---|---|
| API root | `http://127.0.0.1:8000/` |
| OpenAPI / Swagger docs | `http://127.0.0.1:8000/docs` |
| Liveness | `http://127.0.0.1:8000/health/live` |
| Readiness | `http://127.0.0.1:8000/health/ready` |

The liveness endpoint should confirm that the process is running. The readiness endpoint should check essential dependencies such as the relational database. Do not make a liveness probe fail solely because a non-critical external AI provider is temporarily unavailable.

Keep the terminal running while developing. Use **Ctrl+C** to stop the server.

---

## 14. Testing Guide

Run tests in layers. Unit tests should not require live Supabase, Bedrock, Pinecone, LangSmith, or Stripe accounts; mock those external services. Keep a separate integration test suite for real credentials and a dedicated test workspace/index.

### 14.1 Backend quality checks

From `backend/`:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run pytest --cov=app --cov-report=term-missing
```

### 14.2 Database checks

```powershell
uv run alembic current
uv run alembic upgrade head
```

Verify that the expected Atlas tables exist and that foreign keys, unique constraints, indexes, and workspace ownership constraints are present. Test a clean database migration and an upgrade from the previous schema before production deployment.

### 14.3 Health-check smoke tests

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

### 14.4 Supabase authentication tests

- Register a test user through the Next.js UI.
- Sign in and confirm the authenticated user state appears in the application.
- Generate an Supabase access token and call a protected FastAPI endpoint.
- Confirm FastAPI resolves the correct Supabase user ID and workspace membership.
- Call the endpoint without a token and confirm it returns `401`.
- Call with an expired/invalid token and confirm it returns `401`.
- Try to access another user's or workspace's document and confirm the API returns `403` or a non-disclosing `404`, according to the API contract.
- Confirm the project API key is never present in browser network requests or client bundles.

### 14.5 Supabase Storage tests

- Upload an allowed PDF as an authenticated test user.
- Confirm the file is private and the correct owner/workspace permissions are applied.
- Confirm another user cannot read or delete the file.
- Try an unsupported extension, MIME type, oversized file, and malformed file; confirm backend validation rejects it.
- Confirm FastAPI can retrieve the file for ingestion using the correct user-scoped or narrowly scoped server credential.
- Delete a test document and verify its storage/vector cleanup workflow is authorized and audited.

### 14.6 Bedrock and Pinecone integration tests

- Invoke the configured Bedrock chat model with a synthetic prompt.
- Generate a Titan embedding and verify it returns the configured dimension.
- Upsert a small synthetic document into a dedicated test namespace.
- Query that namespace and confirm the expected chunk is retrieved.
- Query from a different tenant/workspace and confirm the first tenant's vectors are not returned.
- Test metadata filters, empty results, Bedrock throttling, Pinecone timeouts, and retry behavior.
- Confirm changing embedding dimensions cannot silently write incompatible vectors into the existing index.

### 14.7 RAG and context-engineering tests

- Upload a small synthetic document with known facts.
- Ask a question whose answer is explicitly present in the document.
- Confirm the response contains the supported answer and source references.
- Ask a question not answered by the document and confirm the system says it does not have enough evidence rather than inventing an answer.
- Test follow-up questions to confirm recent conversation context is included.
- Test long conversations to confirm messages are trimmed/summarized within the configured context budget.
- Test retrieval with irrelevant documents and verify the answer does not cite unrelated sources.
- Test prompt-injection text inside a document and verify retrieved text is treated as untrusted data, not as instructions.

### 14.8 Memory tests

- Confirm the persistent LangChain checkpointer can save and resume a thread after a backend restart.
- Confirm `thread_id` is derived from a server-authorized conversation and cannot be swapped to access another workspace's state.
- Confirm the checkpointer schema is initialized once through a controlled setup/release step.
- Confirm chat messages persist after a backend restart and can be loaded by conversation ID.
- Confirm the configured recent-turn limit is applied.
- Confirm memories are scoped to the correct user/workspace and are not visible across tenants.
- Confirm explicit memory deletion removes the database record and invalidates any derived cache or summary.
- Do not persist sensitive personal or enterprise information into long-term memory unless the product has a clear user-facing purpose, permission, and retention policy.

### 14.9 Human-in-the-loop tests

- Confirm the agent is created with LangChain's `HumanInTheLoopMiddleware` and a persistent PostgreSQL checkpointer; never use an in-memory checkpointer in production.
- Trigger a tool/action that requires approval.
- Confirm the workflow creates a durable `pending` approval record and does not execute the action.
- Confirm only an authorized approver can approve or reject it.
- Confirm rejection prevents execution.
- Confirm approval executes the authorized action once only.
- Confirm duplicate submissions, repeated web requests, or concurrent approvals cannot execute an action twice.
- Confirm approval decisions and subsequent execution attempts are written to the audit trail.

### 14.10 Stripe tests

Use Stripe test-mode keys and a local webhook listener. Install and authenticate the [Stripe CLI](https://docs.stripe.com/stripe-cli), then forward events to the local API:

```powershell
stripe listen --forward-to localhost:8000/api/v1/billing/webhooks/stripe
```

Use the signing secret printed by the CLI as the temporary local `STRIPE_WEBHOOK_SECRET`. Then trigger supported test events or complete a test Checkout Session.

Verify that:

- FastAPI creates Checkout Sessions only for authenticated users and server-configured prices.
- Webhook signatures are verified against the raw request body.
- Invalid signatures are rejected.
- Duplicate event IDs are processed idempotently.
- Subscription state changes only after verified webhook events.
- `invoice.payment_failed` and subscription deletion/revocation remove paid entitlements as defined by product policy.
- A frontend success redirect alone does not grant access.

### 14.11 Frontend checks

From `frontend/`:

```powershell
bun lint
bun exec tsc --noEmit
bun build
```

If a test runner is configured, also run the project's frontend unit and component tests (for example, `bun test`).

### 14.12 LangSmith trace checks

- Confirm a synthetic RAG request creates a trace in the `atlas-enterprise-ai` project.
- Inspect retrieval, prompt, model, tool, and output spans.
- Confirm trace metadata contains useful IDs but no API keys, JWTs, private document text, or unredacted sensitive values.
- Confirm tracing can be disabled or sampled without breaking core API functionality.

---

## 15. Deploy the Backend to FastAPI Cloud

FastAPI Cloud supports `uv`-based projects and deployment from the FastAPI Cloud CLI.

### 15.1 Prepare the backend for deployment

Before deploying:

- Ensure `backend/pyproject.toml` declares all runtime dependencies.
- Commit `backend/uv.lock`.
- Confirm the FastAPI app entrypoint is correct.
- Confirm local health checks and tests pass.
- Ensure no `.env` file, credentials, test documents, or local virtual environment are tracked by Git.
- Ensure the database connection string uses TLS and the correct Supabase PostgreSQL endpoint.

### 15.2 Link and deploy

From the `backend/` directory:

```powershell
uv sync
uv run fastapi login
uv run fastapi deploy
```

Complete the browser sign-in flow if prompted, then select or create your FastAPI Cloud team/application.

If you deploy from a monorepo and the backend lives under `backend/`, configure the FastAPI Cloud application's **Application Directory** as `backend` in the FastAPI Cloud dashboard. The platform then installs dependencies from that directory and runs the app from that working directory. If you are deploying directly while already inside the backend directory, confirm the linked app is configured for the intended application path.

### 15.3 Add FastAPI Cloud environment variables

Open the application in the FastAPI Cloud dashboard and add all required backend environment variables from Section 11. Mark credentials and tokens as **Secrets**, including:

- Supabase service role key (only if required for privileged backend operations).
- Supabase/PostgreSQL connection strings.
- AWS credentials.
- Pinecone API key.
- LangSmith API key.
- Stripe Secret key and webhook signing secret.

Add non-secret settings such as model IDs, environment name, and feature flags as ordinary environment variables if appropriate. FastAPI Cloud applies environment variable changes on the next deployment; use its redeploy option after changing production values.

### 15.4 Run migrations safely

Do not run schema creation automatically every time a FastAPI instance starts. FastAPI Cloud can deploy or scale multiple instances. Run Alembic migrations as a controlled release step using the direct PostgreSQL connection:

```powershell
cd backend
uv sync
uv run alembic upgrade head
```

Use backward-compatible migrations for zero-downtime deployments: add new nullable columns/tables first, deploy code that supports both old and new schema, backfill data, and remove obsolete columns in a later release.

### 15.5 Verify the backend deployment

After deployment:

1. Copy the FastAPI Cloud public URL.
2. Open `/health/live` and `/health/ready`.
3. Open `/docs` if public API docs are enabled.
4. Review deployment logs and runtime logs for missing environment variables or dependency errors.
5. Test Supabase access token authentication, database connectivity, Bedrock invocation, Pinecone retrieval, LangSmith tracing, and Stripe webhook routing using test data.
6. Add the deployed frontend domain to the FastAPI CORS allowlist before browser-to-API production tests.

---

## 16. Deploy the Frontend to Vercel

### 16.1 Import the repository

1. Sign in to [Vercel](https://vercel.com/).
2. Select **Add New → Project**.
3. Import the Atlas Git repository.
4. Set the Root Directory to `frontend` for the monorepo layout described in this guide.
5. Confirm the project framework is detected as Next.js.
6. Keep the detected build settings unless your project has custom scripts.
7. Deploy a Preview first, verify it, then promote/merge to the production branch.

Vercel can create preview deployments for branch pushes and production deployments from the configured production branch.

### 16.2 Configure Vercel environment variables

Add the frontend values from Section 12 in the Vercel project settings. Configure the values separately for Preview and Production where required.

Production examples:

```dotenv
NEXT_PUBLIC_SUPABASE_URL=https://<REGION>.supabase.co/v1
NEXT_PUBLIC_SUPABASE_ANON_KEY=<SUPABASE_ANON_KEY>
SUPABASE_SERVICE_ROLE_KEY=<SUPABASE_SERVICE_ROLE_KEY>
NEXT_PUBLIC_API_BASE_URL=https://<YOUR_FASTAPI_CLOUD_DOMAIN>/api/v1
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=<STRIPE_PUBLISHABLE_KEY_IF_USED>
```

`SUPABASE_SERVICE_ROLE_KEY` must remain server-only. Do not prefix it with `NEXT_PUBLIC_`.

Use Stripe test keys in Preview environments. Use live Stripe keys and the live webhook secret only in Production after the end-to-end test plan is complete.

### 16.3 Configure Supabase Auth URLs and FastAPI CORS

After Vercel deploys:

1. Copy the Vercel production domain, such as `https://your-atlas-app.vercel.app`.
2. Add that hostname as a Web platform in Supabase.
3. Add any stable custom domain that you attach to the production frontend.
4. Add Preview hostnames or an appropriately restricted preview redirect URLs if preview builds need Auth.
5. Update FastAPI Cloud `CORS_ORIGINS` to include the exact frontend production origin and any required preview origins.
6. Redeploy the backend after updating its environment variables.

Do not use `*` as the production CORS origin when credentials or authenticated browser requests are involved. Keep the list restricted to your actual frontend domains.

### 16.4 Final frontend deployment verification

- Open the Vercel production URL.
- Register and sign in with a test user.
- Confirm SSR session state and protected routes work after a page refresh.
- Upload a private test document.
- Ask a RAG question and confirm source references appear.
- Verify the browser calls the correct FastAPI Cloud URL.
- Verify that no server-side secret appears in browser source, network requests, or client bundle output.
- Complete a Stripe test checkout and verify subscription state only changes after the verified webhook is processed.

---

## 17. Production Readiness Checklist

### Application and dependencies

- [ ] Python version is pinned and supported.
- [ ] `pyproject.toml` and `uv.lock` are committed.
- [ ] Frontend lockfile is committed.
- [ ] `.env`, `.env.local`, credentials, `.venv`, and uploaded documents are excluded from Git.
- [ ] Unit tests, lint checks, type checks, and production builds pass.

### Supabase

- [ ] Production and required Preview domains are registered as Web platforms.
- [ ] Auth methods and verification settings match product policy.
- [ ] Supabase service role key is server-only and minimally scoped.
- [ ] Private Storage bucket and file-level permissions are enabled.
- [ ] User JWTs are validated on protected FastAPI endpoints.
- [ ] Workspace membership and resource authorization are checked server-side.

### PostgreSQL and data

- [ ] Supabase **Supabase PostgreSQL** is used for SQLModel.
- [ ] Runtime and migration connection strings are configured correctly.
- [ ] TLS is required for database connections.
- [ ] Alembic migrations are reviewed and applied.
- [ ] Backups/retention and recovery settings are appropriate for the data.
- [ ] Production startup does not automatically create or destructively alter tables.

### AI and retrieval

- [ ] Bedrock model access is enabled in the selected region.
- [ ] Chat and embedding model IDs are verified.
- [ ] Pinecone dimension matches the embedding output.
- [ ] Namespace is derived from the authenticated tenant/workspace.
- [ ] Retrieval filters and application authorization are enforced together.
- [ ] Context length and memory limits are configured.
- [ ] Guardrails and approval-required actions are tested.
- [ ] LangSmith traces redact or omit sensitive content.

### Payments and deployment

- [ ] Stripe webhook signature verification is enabled.
- [ ] Webhook event processing is idempotent.
- [ ] Entitlements are based on verified Stripe events, not frontend redirects.
- [ ] FastAPI Cloud secrets are stored as encrypted secrets.
- [ ] Vercel Preview and Production environment variables are separated.
- [ ] Supabase Auth redirect allow-list and FastAPI CORS include the correct frontend domains.
- [ ] Health checks, logs, and deployment rollback procedures are understood.

---

## 18. Common Problems and Troubleshooting

| Problem | Likely cause | What to check |
|---|---|---|
| `uv sync` fails | Python version or dependency resolution issue | Check `.python-version`, `pyproject.toml`, and lockfile; run `uv lock` only when intentionally updating dependencies |
| FastAPI Cloud cannot find the app | Wrong application directory or entrypoint | Confirm the Supabase repo path, FastAPI Cloud Application Directory, and app entrypoint |
| Database connection fails | Wrong DSN, port, password encoding, or TLS setting | Copy fresh credentials from Supabase; use pooler `6432` for runtime and direct `5432` for migrations; require TLS |
| Migration hangs or fails | Pooler used for a migration or schema mismatch | Use the direct PostgreSQL connection for migration commands and inspect the generated migration |
| SQLModel cannot connect to TablesDB (rejected) | TablesDB is not a raw PostgreSQL endpoint | Use Supabase PostgreSQL for SQLModel, or redesign persistence around the TablesDB SDK |
| Supabase Auth / browser CORS error | Missing Web platform hostname | Add `localhost`, Vercel production domain, and required preview domains to Supabase Auth redirect allow-list |
| FastAPI returns `401` | Missing, invalid, expired, or incorrectly forwarded Supabase access token | Generate a fresh JWT after login; pass it in the expected request header; validate using a request-scoped Supabase client / JWT verification |
| User can see another tenant's data | Missing workspace authorization or unsafe namespace selection | Resolve tenant from verified identity; derive Pinecone namespace server-side; filter database and vector queries by workspace |
| File upload is forbidden | Bucket/file permissions do not grant the user access | Check bucket/file security, per-file permissions, user session, and allowed file size/type |
| Bedrock access denied | Missing IAM permission or model not available in region | Check the IAM policy, model access, region, and exact model ID |
| Pinecone dimension error | Index dimension differs from embedding output | Check embedding configuration and index dimension; rebuild/reindex after model changes |
| Pinecone data leak across workspaces | Namespace or metadata filter not enforced | Derive namespace on the backend and apply workspace metadata filter on every retrieval request |
| No LangSmith traces | Tracing disabled or invalid key/project | Check `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, and outbound network access |
| Stripe webhook returns signature error | Wrong endpoint secret or request body was parsed before verification | Use the exact endpoint's signing secret and verify against the original raw request body |
| Duplicate Stripe state updates | Webhook handler is not idempotent | Persist Stripe event IDs with a unique constraint and safely ignore already-processed events |
| Frontend cannot reach API after deployment | Incorrect API URL or CORS origins | Check Vercel `NEXT_PUBLIC_API_BASE_URL`, FastAPI Cloud CORS, and redeploy after environment changes |
| Production environment variable appears missing | Secret was not saved/redeployed or was added to the wrong environment | Verify Preview vs Production scope and trigger a new deployment |

---

## 19. Official Documentation and Reference Links

### Original Atlas guide

- [Original Complete Setup and Testing Guide](https://github.com/entbappy/ATLAS-Enterprise-AI/blob/main/docs/1.%20Complete_Setup_and_Testing_Guide.md)

### `uv` and FastAPI Cloud

- [uv — Working on projects](https://docs.astral.sh/uv/guides/projects/)
- [FastAPI Cloud — Quick start](https://fastapicloud.com/docs/getting-started/)
- [FastAPI Cloud — Deploy command](https://fastapicloud.com/docs/fastapi-cloud-cli/deploy/)
- [FastAPI Cloud — Environment variables and secrets](https://fastapicloud.com/docs/builds-and-deployments/environment-variables/)
- [FastAPI Cloud — Application directory / monorepo](https://fastapicloud.com/docs/builds-and-deployments/application-directory/)
- [FastAPI Cloud — Database migrations and zero-downtime deployments](https://fastapicloud.com/docs/builds-and-deployments/database-migrations/)

### Supabase

- [Supabase documentation](https://supabase.com/docs)
- [Supabase Auth](https://supabase.com/docs/guides/auth)
- [Supabase Auth with Next.js](https://supabase.com/docs/guides/auth/server-side/nextjs)
- [Supabase SSR (`@supabase/ssr`)](https://supabase.com/docs/guides/auth/server-side/creating-a-client)
- [Supabase Database (Postgres)](https://supabase.com/docs/guides/database/overview)
- [Supabase connection pooling](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)
- [Supabase Storage](https://supabase.com/docs/guides/storage)
- [Supabase Storage Access Control](https://supabase.com/docs/guides/storage/security/access-control)
- [Supabase Python client](https://supabase.com/docs/reference/python/introduction)


### Amazon Bedrock, LangChain, Pinecone, and LangSmith

- [Amazon Bedrock](https://docs.aws.amazon.com/bedrock/)
- [LangChain — Amazon Bedrock integrations](https://docs.langchain.com/oss/python/integrations/chat/bedrock_converse)
- [LangChain — Embedding integrations](https://docs.langchain.com/oss/python/integrations/embeddings)
- [LangChain — Short-term memory and PostgreSQL checkpointer](https://docs.langchain.com/oss/python/langchain/short-term-memory)
- [LangChain — Human-in-the-loop middleware and persistent checkpointer](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)
- [LangChain — Bedrock chat model reference (`ChatBedrockConverse`)](https://reference.langchain.com/python/langchain-aws/chat_models/bedrock_converse/ChatBedrockConverse)
- [LangChain — Bedrock embeddings](https://docs.langchain.com/oss/python/integrations/embeddings/bedrock)
- [LangChain — Middleware and guardrail building blocks](https://docs.langchain.com/oss/python/langchain/middleware/overview)
- [LangChain — Context engineering](https://docs.langchain.com/oss/python/deepagents/context-engineering)
- [LangSmith — Observability](https://docs.langchain.com/oss/python/langchain/observability)
- [Pinecone — Documentation](https://docs.pinecone.io/)
- [Pinecone — Index configuration](https://docs.pinecone.io/reference/api/2025-10/control-plane/configure_index)

### Stripe and Vercel

- [Stripe — Checkout](https://docs.stripe.com/checkout)
- [Stripe — Webhooks](https://docs.stripe.com/webhooks)
- [Stripe — Stripe CLI](https://docs.stripe.com/stripe-cli)
- [Vercel — Deploying Git repositories](https://vercel.com/docs/git)
- [Vercel — Environment variables](https://vercel.com/docs/environment-variables)
- [Next.js — Deployment](https://nextjs.org/docs/app/guides/deploying)

---

## 20. Final Setup Sequence

Use this order for a clean first-time setup:

1. Install `uv`, Python, Node.js, and `bun`.
2. Prepare the backend repository and run `uv sync`.
3. Create the Supabase project and register the local web platform.
4. Configure Supabase Auth and the Supabase JS/SSR SSR integration.
5. Create the private Supabase Storage bucket and file permissions.
6. Create Supabase PostgreSQL and configure runtime/migration DSNs.
7. Configure Alembic and apply the initial SQLModel migration.
8. Enable Amazon Bedrock chat and embedding models; configure IAM credentials.
9. Create the 1024-dimensional cosine Pinecone index and define the tenant namespace strategy.
10. Create the LangSmith project and configure tracing with data redaction.
11. Configure Stripe products/prices and test credentials.
12. Create backend `.env` from `.env.example` and verify all integrations locally.
13. Configure the Next.js frontend, Supabase Auth helpers (@supabase/ssr / @supabase/supabase-js), shadcn/ui, and `.env.local`.
14. Run backend, frontend, RAG, memory, HITL, storage, and payment tests.
15. Deploy FastAPI to FastAPI Cloud and set encrypted backend secrets.
16. Apply production database migrations using the direct PostgreSQL connection.
17. Deploy Next.js to Vercel and configure Preview/Production environment variables.
18. Register Vercel domains in Supabase and update FastAPI CORS origins.
19. Configure the live Stripe webhook endpoint and verify the complete production flow.
20. Complete the production readiness checklist before inviting real users.

**Deployment target:** Next.js on Vercel → FastAPI on FastAPI Cloud → Supabase Auth / private Storage / Supabase PostgreSQL → LangChain + Amazon Bedrock → Pinecone → LangSmith; Stripe webhooks enter through FastAPI Cloud.
