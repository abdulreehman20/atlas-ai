"""Allowlisted tool execution after HITL approval."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.ai.vector_store import VectorStoreClient
from app.core.exceptions import ForbiddenError
from app.core.security import Principal
from app.db.models.approval import Approval
from app.db.models.enums import MembershipStatus
from app.db.models.membership import WorkspaceMembership
from app.services import documents as document_service
from app.services.storage import StorageClient

# Tools the approval executor is allowed to run after Owner approve.
ALLOWLISTED_TOOLS = {
    "noop",
    "document.delete",
    "membership.remove",
}


def execute_approved_tool(
    session: Session,
    *,
    principal: Principal,
    approval: Approval,
    storage: StorageClient | None = None,
    vectors: VectorStoreClient | None = None,
) -> dict[str, Any]:
    tool = approval.tool_name
    if tool not in ALLOWLISTED_TOOLS:
        raise ForbiddenError(f"Tool not allowlisted for execution: {tool}")

    args = approval.sanitized_arguments or {}

    if tool == "noop":
        return {"ok": True, "tool": tool}

    if tool == "document.delete":
        if storage is None or vectors is None:
            raise ForbiddenError("Storage and vector clients required for document.delete")
        document_id = UUID(str(args["document_id"]))
        doc = document_service.delete_document(
            session,
            principal=principal,
            document_id=document_id,
            storage=storage,
            vectors=vectors,
            request_id=None,
        )
        return {"ok": True, "tool": tool, "document_id": str(doc.id), "status": doc.status}

    if tool == "membership.remove":
        membership_id = UUID(str(args["membership_id"]))
        row = session.get(WorkspaceMembership, membership_id)
        if row is None or row.workspace_id != principal.workspace_id:
            raise ForbiddenError("Membership not found in workspace")
        if row.role == "owner":
            raise ForbiddenError("Cannot remove the owner")
        row.status = MembershipStatus.REMOVED.value
        session.add(row)
        session.commit()
        return {"ok": True, "tool": tool, "membership_id": str(row.id), "status": row.status}

    raise ForbiddenError(f"Unhandled allowlisted tool: {tool}")
