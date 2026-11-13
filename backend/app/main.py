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
    return application


app = create_app()
