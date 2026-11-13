"""Organization entity."""

from __future__ import annotations

from sqlmodel import Field

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import OrgStatus


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    __tablename__ = "organizations"

    name: str = Field(max_length=255)
    slug: str = Field(max_length=255, unique=True, index=True)
    status: str = Field(default=OrgStatus.ACTIVE.value, max_length=32)
    system_prompt_override: str | None = Field(default=None)
