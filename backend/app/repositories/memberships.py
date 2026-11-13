"""Membership repository."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.db.models.enums import MembershipStatus
from app.db.models.membership import WorkspaceMembership


def get_active_membership(
    session: Session,
    *,
    supabase_user_id: str,
) -> WorkspaceMembership | None:
    statement = select(WorkspaceMembership).where(
        WorkspaceMembership.supabase_user_id == supabase_user_id,
        WorkspaceMembership.status == MembershipStatus.ACTIVE.value,
    )
    return session.exec(statement).first()


def get_membership_by_workspace_user(
    session: Session,
    *,
    workspace_id: UUID,
    supabase_user_id: str,
) -> WorkspaceMembership | None:
    statement = select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.supabase_user_id == supabase_user_id,
        WorkspaceMembership.status == MembershipStatus.ACTIVE.value,
    )
    return session.exec(statement).first()


def count_active_members(session: Session, *, workspace_id: UUID) -> int:
    statement = select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.status == MembershipStatus.ACTIVE.value,
    )
    return len(list(session.exec(statement).all()))
