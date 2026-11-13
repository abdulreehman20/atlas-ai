"""HITL approval routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import PrincipalDep, RequestIdDep, SessionDep
from app.schemas.approvals import (
    ApprovalCreateRequest,
    ApprovalDecisionRequest,
    ApprovalResponse,
)
from app.services import approvals as approval_service

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalResponse])
def list_approvals(
    principal: PrincipalDep,
    session: SessionDep,
) -> list[ApprovalResponse]:

    rows = approval_service.list_approvals(session, principal=principal)
    return [ApprovalResponse.model_validate(row) for row in rows]


@router.post("", response_model=ApprovalResponse)
def create_approval(
    body: ApprovalCreateRequest,
    principal: PrincipalDep,
    session: SessionDep,
    request_id: RequestIdDep,
) -> ApprovalResponse:

    row = approval_service.create_approval(
        session,
        principal=principal,
        action=body.action,
        tool_name=body.tool_name,
        summary=body.summary,
        sanitized_arguments=body.sanitized_arguments,
        checkpoint_thread_id=body.checkpoint_thread_id,
        request_id=request_id,
    )
    return ApprovalResponse.model_validate(row)


@router.post("/{approval_id}/decision", response_model=ApprovalResponse)
def decide_approval(
    approval_id: UUID,
    body: ApprovalDecisionRequest,
    principal: PrincipalDep,
    session: SessionDep,
    request_id: RequestIdDep,
) -> ApprovalResponse:

    row = approval_service.decide_approval(
        session,
        principal=principal,
        approval_id=approval_id,
        decision=body.decision,
        note=body.note,
        request_id=request_id,
    )
    return ApprovalResponse.model_validate(row)
