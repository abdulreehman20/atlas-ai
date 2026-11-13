"""Audit event recording."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.db.models.audit_event import AuditEvent


def record_audit(
    session: Session,
    *,
    action: str,
    actor_user_id: str | None = None,
    organization_id: UUID | None = None,
    workspace_id: UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        workspace_id=workspace_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=metadata,
        request_id=request_id,
        trace_id=trace_id,
    )
    session.add(event)
    return event
