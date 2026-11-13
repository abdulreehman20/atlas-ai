"""Shared API schemas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# DELETE -- This is not in use. Exception handlers do not return this schema.
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    checks: dict[str, str] = Field(default_factory=dict)


# DELETE -- This is not in use. /me returns a raw dict instead.
class MeResponse(APIModel):
    user_id: str
    email: str | None
    organization_id: UUID
    workspace_id: UUID
    role: str
    plan_tier: str
