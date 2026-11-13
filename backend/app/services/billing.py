"""Stripe billing, webhooks, and entitlement updates."""

# DELETE -- This is not in use. Routes reimplement checkout/portal/webhook inline
# in app/api/v1/routes/billing.py. Prefer wiring routes to this service later, or remove.

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import stripe
from sqlmodel import Session, select

from app.core.config import Settings
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.security import Principal
from app.db.models.billing_customer import BillingCustomer
from app.db.models.enums import PlanTier, SubscriptionStatus, UsageOperation
from app.db.models.stripe_webhook_event import StripeWebhookEvent
from app.db.models.subscription import Subscription
from app.repositories import documents as document_repo
from app.repositories import usage as usage_repo
from app.schemas.billing import EntitlementResponse
from app.services.auth import require_role
from app.services.entitlements import get_entitlements_for_org


def _configure_stripe(settings: Settings) -> None:
    stripe.api_key = settings.stripe_secret_key


def get_or_create_customer(
    session: Session,
    settings: Settings,
    *,
    principal: Principal,
) -> BillingCustomer:
    require_role(principal, "owner")
    existing = session.exec(
        select(BillingCustomer).where(BillingCustomer.organization_id == principal.organization_id)
    ).first()
    if existing is not None:
        return existing

    _configure_stripe(settings)
    customer = stripe.Customer.create(
        email=principal.email,
        metadata={
            "organization_id": str(principal.organization_id),
            "workspace_id": str(principal.workspace_id),
            "user_id": principal.user_id,
        },
    )
    record = BillingCustomer(
        organization_id=principal.organization_id,
        stripe_customer_id=customer["id"],
        billing_email=principal.email,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def create_checkout_session(
    session: Session,
    settings: Settings,
    *,
    principal: Principal,
    success_url: str,
    cancel_url: str,
) -> dict[str, str]:
    require_role(principal, "owner")
    if not settings.stripe_price_id:
        raise AppError(
            "STRIPE_PRICE_ID is not configured",
            code="stripe_not_configured",
            status_code=500,
        )
    customer = get_or_create_customer(session, settings, principal=principal)
    _configure_stripe(settings)
    checkout = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer.stripe_customer_id,
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"organization_id": str(principal.organization_id)},
    )
    return {"checkout_url": checkout["url"], "session_id": checkout["id"]}


def create_portal_session(
    session: Session,
    settings: Settings,
    *,
    principal: Principal,
    return_url: str,
) -> dict[str, str]:
    require_role(principal, "owner")
    customer = get_or_create_customer(session, settings, principal=principal)
    _configure_stripe(settings)
    portal = stripe.billing_portal.Session.create(
        customer=customer.stripe_customer_id,
        return_url=return_url,
    )
    return {"portal_url": portal["url"]}


def entitlement_snapshot(
    session: Session,
    settings: Settings,
    *,
    principal: Principal,
) -> EntitlementResponse:
    entitlements = get_entitlements_for_org(
        session, settings, organization_id=principal.organization_id
    )
    docs = document_repo.count_active_documents(session, workspace_id=principal.workspace_id)
    storage = document_repo.sum_storage_bytes(session, workspace_id=principal.workspace_id)
    chats = usage_repo.count_usage(
        session,
        organization_id=principal.organization_id,
        operation=UsageOperation.CHAT,
    )
    return EntitlementResponse(
        plan_tier=entitlements.plan_tier.value,
        member_limit=entitlements.member_limit,
        document_limit=entitlements.document_limit,
        max_file_size_mib=entitlements.max_file_size_mib,
        storage_mib=entitlements.storage_mib,
        chat_monthly_limit=entitlements.chat_monthly_limit,
        custom_system_prompt=entitlements.custom_system_prompt,
        documents_used=docs,
        chats_used_this_month=chats,
        storage_used_bytes=storage,
    )


def process_stripe_webhook(
    session: Session,
    settings: Settings,
    *,
    payload: bytes,
    signature: str,
) -> StripeWebhookEvent:
    if not settings.stripe_webhook_secret:
        raise AppError(
            "STRIPE_WEBHOOK_SECRET is not configured",
            code="stripe_not_configured",
            status_code=500,
        )
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=settings.stripe_webhook_secret,
        )
    except Exception as exc:  # noqa: BLE001
        raise ForbiddenError("Invalid Stripe signature") from exc

    event_id = event["id"]
    existing = session.exec(
        select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == event_id)
    ).first()
    if existing is not None:
        raise ConflictError("Webhook already processed")

    record = StripeWebhookEvent(
        stripe_event_id=event_id,
        event_type=event["type"],
        status="received",
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    try:
        _apply_event(session, settings, event=event)
        record.status = "processed"
        record.processed_at = datetime.now(UTC)
        session.add(record)
        session.commit()
    except Exception as exc:  # noqa: BLE001
        record.status = "failed"
        record.error_message = str(exc)[:1000]
        session.add(record)
        session.commit()
        raise
    session.refresh(record)
    return record


def _apply_event(session: Session, settings: Settings, *, event: dict[str, Any]) -> None:
    event_type = event["type"]
    data_object = event["data"]["object"]
    if event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        _upsert_subscription_from_stripe(session, settings, data_object)
        return
    if event_type == "checkout.session.completed":
        subscription_id = data_object.get("subscription")
        customer_id = data_object.get("customer")
        if subscription_id and customer_id:
            _configure_stripe(settings)
            sub = stripe.Subscription.retrieve(subscription_id)
            _upsert_subscription_from_stripe(session, settings, sub)
        return
    # Unknown events are acknowledged without mutation.


def _upsert_subscription_from_stripe(
    session: Session,
    settings: Settings,
    stripe_sub: Any,
) -> None:
    customer_id = stripe_sub["customer"]
    billing = session.exec(
        select(BillingCustomer).where(BillingCustomer.stripe_customer_id == customer_id)
    ).first()
    if billing is None:
        raise NotFoundError("Billing customer not found for Stripe customer")

    subscription = session.exec(
        select(Subscription).where(Subscription.organization_id == billing.organization_id)
    ).first()
    if subscription is None:
        subscription = Subscription(organization_id=billing.organization_id)
        session.add(subscription)

    status = str(stripe_sub.get("status", SubscriptionStatus.NONE.value))
    price_id = None
    items = stripe_sub.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")

    subscription.stripe_subscription_id = stripe_sub.get("id")
    subscription.stripe_price_id = price_id
    subscription.status = status
    if status in {SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value}:
        if price_id == settings.stripe_price_id or settings.stripe_price_id == "":
            subscription.plan_tier = PlanTier.PRO.value
        else:
            subscription.plan_tier = PlanTier.PRO.value
    elif status == SubscriptionStatus.CANCELED.value:
        subscription.plan_tier = PlanTier.FREE.value
    else:
        # past_due / unpaid keep prior tier until canceled policy applies; Free for safety.
        if status in {SubscriptionStatus.UNPAID.value}:
            subscription.plan_tier = PlanTier.FREE.value

    period_start = stripe_sub.get("current_period_start")
    period_end = stripe_sub.get("current_period_end")
    if period_start:
        subscription.current_period_start = datetime.fromtimestamp(period_start, tz=UTC)
    if period_end:
        subscription.current_period_end = datetime.fromtimestamp(period_end, tz=UTC)
    subscription.cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
    session.add(subscription)
    session.commit()
