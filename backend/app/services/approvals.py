"""Human-in-the-loop approval records."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Never
from uuid import UUID

from sqlmodel import Session, select

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.security import Principal
from app.db.models.approval import Approval
from app.db.models.enums import ApprovalStatus
from app.services.audit import record_audit
from app.services.auth import require_role


def create_approval(
    session: Session,
    *,
    principal: Principal,
    action: str,
    tool_name: str,
    summary: str,
    sanitized_arguments: dict[str, Any] | None = None,
    checkpoint_thread_id: str | None = None,
    request_id: str | None = None,
) -> Approval:

    approval = Approval(
        workspace_id=principal.workspace_id,
        organization_id=principal.organization_id,
        requester_user_id=principal.user_id,
        action=action,
        tool_name=tool_name,
        summary=summary,
        sanitized_arguments=sanitized_arguments,
        checkpoint_thread_id=checkpoint_thread_id,
        status=ApprovalStatus.PENDING.value,
    )
    session.add(approval)

    record_audit(
        session,
        action="approval.created",
        actor_user_id=principal.user_id,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        target_type="approval",
        request_id=request_id,
    )
    session.commit()
    session.refresh(approval)

    return approval


def list_approvals(session: Session, *, principal: Principal) -> list[Approval]:
    statement = (
        select(Approval)
        .where(Approval.workspace_id == principal.workspace_id)
        .order_by(Approval.created_at.desc())
    )
    return list(session.exec(statement).all())


def decide_approval(
    session: Session,
    *,
    principal: Principal,
    approval_id: UUID,
    decision: Literal["approve", "reject"],
    note: str | None = None,
    request_id: str | None = None,
) -> Approval:

    require_role(principal, "owner")
    approval = session.get(Approval, approval_id)
    if approval is None or approval.workspace_id != principal.workspace_id:
        raise NotFoundError("Approval not found")
    if approval.status != ApprovalStatus.PENDING.value:
        raise ForbiddenError("Approval is not pending")

    if decision == "approve":
        approval.status = ApprovalStatus.APPROVED.value
    elif decision == "reject":
        approval.status = ApprovalStatus.REJECTED.value
    else:
        never_decision: Never = decision
        raise ForbiddenError(f"Unsupported decision: {never_decision}")

    approval.reviewer_user_id = principal.user_id
    approval.decision_note = note
    approval.decided_at = datetime.now(UTC)
    session.add(approval)
    record_audit(
        session,
        action=f"approval.{decision}",
        actor_user_id=principal.user_id,
        organization_id=principal.organization_id,
        workspace_id=principal.workspace_id,
        target_type="approval",
        target_id=str(approval.id),
        request_id=request_id,
    )
    session.commit()
    session.refresh(approval)
    return approval
