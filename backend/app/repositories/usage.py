"""Usage metering repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.db.models.enums import UsageOperation
from app.db.models.usage_record import UsageRecord


def current_period_key(now: datetime | None = None) -> str:
    stamp = now or datetime.now(UTC)
    return stamp.strftime("%Y-%m")


def count_usage(
    session: Session,
    *,
    organization_id: UUID,
    operation: UsageOperation,
    period_key: str | None = None,
) -> int:
    key = period_key or current_period_key()
    statement = select(UsageRecord).where(
        UsageRecord.organization_id == organization_id,
        UsageRecord.operation == operation.value,
        UsageRecord.period_key == key,
    )
    return sum(record.units for record in session.exec(statement).all())


def add_usage(
    session: Session,
    *,
    workspace_id: UUID,
    organization_id: UUID,
    user_id: str | None,
    operation: UsageOperation,
    units: int = 1,
    model_id: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    request_id: str | None = None,
) -> UsageRecord:
    record = UsageRecord(
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        operation=operation.value,
        units=units,
        model_id=model_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        period_key=current_period_key(),
        request_id=request_id,
    )
    session.add(record)
    return record
