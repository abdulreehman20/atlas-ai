"""Membership repository."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from app.db.models.base import utcnow
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


def get_pending_invite_by_email(
    session: Session,
    *,
    email: str,
) -> WorkspaceMembership | None:
    normalized = email.strip().lower()
    statement = (
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.email == normalized,
            WorkspaceMembership.status == MembershipStatus.INVITED.value,
        )
        .order_by(col(WorkspaceMembership.created_at).desc())
    )
    return session.exec(statement).first()


def activate_invite(
    session: Session,
    *,
    membership: WorkspaceMembership,
    supabase_user_id: str,
    email: str | None = None,
) -> WorkspaceMembership:
    membership.supabase_user_id = supabase_user_id
    membership.status = MembershipStatus.ACTIVE.value
    membership.joined_at = utcnow()
    if email:
        membership.email = email.strip().lower()
    session.add(membership)
    session.commit()
    session.refresh(membership)
    return membership


def count_active_members(session: Session, *, workspace_id: UUID) -> int:
    statement = select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.status == MembershipStatus.ACTIVE.value,
    )
    return len(list(session.exec(statement).all()))
    

def count_seat_members(session: Session, *, workspace_id: UUID) -> int:
    """Count seats that consume the plan member limit (active + pending invites)."""
    statement = select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id,
        col(WorkspaceMembership.status).in_(
            [MembershipStatus.ACTIVE.value, MembershipStatus.INVITED.value]
        ),
    )
    return len(list(session.exec(statement).all()))
