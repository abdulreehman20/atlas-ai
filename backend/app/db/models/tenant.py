"""Deprecated. Use organization/workspace/membership modules."""

from app.db.models.membership import WorkspaceMembership
from app.db.models.organization import Organization
from app.db.models.workspace import Workspace

__all__ = ["Organization", "Workspace", "WorkspaceMembership"]
