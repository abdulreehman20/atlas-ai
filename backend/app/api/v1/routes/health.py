"""Liveness and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SettingsDep
from app.db.engine import get_engine
from app.schemas.common import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
def ready(settings: SettingsDep) -> HealthResponse:
    checks: dict[str, str] = {}
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    checks["jwt"] = "ok" if settings.has_jwt_verifier() or settings.app_env == "test" else "missing"
    status = "ok" if checks.get("database") == "ok" else "degraded"
    return HealthResponse(status=status, checks=checks)


@router.get("/sentry-debug")
async def trigger_error():
    return 1 / 0
