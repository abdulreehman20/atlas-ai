"""Billing and usage schemas."""

# DELETE -- Most types below are not in use by live routes (billing/usage return dicts).
# EntitlementResponse is only referenced by orphaned services/billing.py.

from __future__ import annotations

from pydantic import Field, HttpUrl

from app.schemas.common import APIModel


# DELETE -- This is not in use.
class CheckoutRequest(APIModel):
    success_url: HttpUrl
    cancel_url: HttpUrl


# DELETE -- This is not in use.
class CheckoutResponse(APIModel):
    checkout_url: str
    session_id: str


# DELETE -- This is not in use.
class PortalRequest(APIModel):
    return_url: HttpUrl


# DELETE -- This is not in use.
class PortalResponse(APIModel):
    portal_url: str


# DELETE -- This is not in use by live routes (only orphaned services/billing.py).
class EntitlementResponse(APIModel):
    plan_tier: str
    member_limit: int
    document_limit: int
    max_file_size_mib: int
    storage_mib: int
    chat_monthly_limit: int
    custom_system_prompt: bool
    documents_used: int
    chats_used_this_month: int
    storage_used_bytes: int


# DELETE -- This is not in use.
class UsageSummaryResponse(APIModel):
    period_key: str
    chats: int
    uploads: int
    entitlements: EntitlementResponse


# DELETE -- This is not in use.
class WorkspacePromptUpdateRequest(APIModel):
    system_prompt_override: str | None = Field(default=None, max_length=8000)
