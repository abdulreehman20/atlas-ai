"""Approval HITL schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel


class ApprovalCreateRequest(APIModel):
    action: str = Field(min_length=1, max_length=128)
    tool_name: str = Field(min_length=1, max_length=128)
    summary: str = Field(min_length=1, max_length=4000)
    sanitized_arguments: dict[str, Any] | None = None
    checkpoint_thread_id: str | None = None


class ApprovalDecisionRequest(APIModel):
    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=1024)


class ApprovalResponse(APIModel):
    id: UUID
    action: str
    tool_name: str
    summary: str
    status: str
    requester_user_id: str
    reviewer_user_id: str | None
    created_at: datetime
    decided_at: datetime | None
