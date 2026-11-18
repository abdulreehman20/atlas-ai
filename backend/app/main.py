"""Atlas Enterprise AI FastAPI application entrypoint."""

from __future__ import annotations

import uuid

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.api.v1.routes import health as health_routes
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import lifespan


def create_app() -> FastAPI:
    settings = get_settings()

    if settings.sentry_dsn:  # add this to Settings + .env
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=1.0 if settings.app_env == "development" else 0.1,
            profile_session_sample_rate=1.0 if settings.app_env == "development" else 0.1,
            profile_lifecycle="trace",
            environment=settings.app_env,
        )

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "Health check"},
            {"name": "me", "description": "Current principal and entitlements"},
            {"name": "auth", "description": "Supabase Auth (signup / login / refresh / logout)"},
            {"name": "workspaces", "description": "Workspace settings and members"},
            {"name": "documents", "description": "Document upload, reprocess, delete"},
            {"name": "ingestion", "description": "Ingestion jobs"},
            {"name": "chat", "description": "RAG chat (sync + stream)"},
            {"name": "feedback", "description": "Chat feedback"},   
            {"name": "conversations", "description": "Conversation history"},
            {"name": "memory", "description": "Long-term memory records"},
            {"name": "approvals", "description": "Human-in-the-loop approvals"},
            {"name": "billing", "description": "Stripe billing"},
            {"name": "usage", "description": "Usage summaries"},
        ],
    )
    register_exception_handlers(application)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,    
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Probe paths at root; versioned API under configured prefix.
    application.include_router(health_routes.router)
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    def custom_openapi():
        if application.openapi_schema:
            return application.openapi_schema
        from fastapi.openapi.utils import get_openapi

        schema = get_openapi(
            title=application.title,
            version=application.version,
            routes=application.routes,
            tags=application.openapi_tags,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})["HTTPBearer"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Paste a Supabase access_token. Use POST /api/v1/auth/login first, "
                "then Authorize with the returned access_token."
            ),
        }
        application.openapi_schema = schema
        return application.openapi_schema

    application.openapi = custom_openapi  # type: ignore[method-assign]
    return application


app = create_app()
