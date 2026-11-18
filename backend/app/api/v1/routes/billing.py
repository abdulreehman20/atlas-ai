from __future__ import annotations

from typing import Annotated
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, Request
from sqlmodel import select

from app.api.deps import PrincipalDep, SessionDep, SettingsDep
from app.core.exceptions import AppError, NotFoundError
from app.core.security import Principal
from app.db.models.base import utcnow
from app.db.models.billing import BillingCustomer, StripeWebhookEvent, Subscription
from app.db.models.enums import PlanTier, SubscriptionStatus
from app.services.auth import require_role

router = APIRouter(prefix="/billing", tags=["billing"])


# NOTE: Duplicate of workspaces.require_owner/OwnerDep — consolidate into app.api.deps later.
def require_owner(principal: PrincipalDep) -> Principal:
    require_role(principal, "owner")
    return principal


OwnerDep = Annotated[Principal, Depends(require_owner)]


@router.get("/subscription")
def subscription_status(principal: PrincipalDep, session: SessionDep) -> dict:
    sub = session.exec(
        select(Subscription).where(Subscription.organization_id == principal.organization_id)
    ).first()
    status = sub.status if sub else SubscriptionStatus.NONE.value
    plan_tier = sub.plan_tier if sub else PlanTier.FREE.value

    if status in {SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value}:
        if sub and sub.plan_tier == PlanTier.PRO.value:
            plan_tier = PlanTier.PRO.value

    return {
        "status": status,
        "plan_tier": plan_tier,
        "stripe_price_id": sub.stripe_price_id if sub else None,
        "cancel_at_period_end": sub.cancel_at_period_end if sub else False,
    }


@router.post("/checkout")
def create_checkout(principal: OwnerDep, session: SessionDep, settings: SettingsDep) -> dict:
    if not settings.stripe_secret_key or not settings.stripe_price_id:
        raise AppError("Stripe is not configured", code="stripe_config", status_code=503)

    stripe.api_key = settings.stripe_secret_key
    customer = session.exec(
        select(BillingCustomer).where(BillingCustomer.organization_id == principal.organization_id)
    ).first()

    if customer is None:
        created = stripe.Customer.create(
            email=principal.email,
            name=(principal.email or "Atlas customer").split("@")[0],
            metadata={"organization_id": str(principal.organization_id)},
        )
        customer = BillingCustomer(
            organization_id=principal.organization_id,
            stripe_customer_id=created["id"],
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)
    else:
        # Ensure name exists for India export-compliance Checkout sessions.
        try:
            stripe.Customer.modify(
                customer.stripe_customer_id,
                name=(principal.email or "Atlas customer").split("@")[0],
            )
        except Exception:  # noqa: BLE001 — checkout still collects address below
            pass

    session_obj = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer.stripe_customer_id,
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        # India RBI/export rules require full billing name + address on Checkout.
        billing_address_collection="required",
        customer_update={"address": "auto", "name": "auto"},
        success_url=f"{settings.frontend_url.rstrip('/')}/settings?checkout=success#billing",
        cancel_url=f"{settings.frontend_url.rstrip('/')}/settings?checkout=cancel#billing",
        metadata={"organization_id": str(principal.organization_id)},
        subscription_data={"metadata": {"organization_id": str(principal.organization_id)}},
    )

    return {"checkout_url": session_obj["url"], "id": session_obj["id"]}


@router.post("/portal")
def create_portal(principal: OwnerDep, session: SessionDep, settings: SettingsDep) -> dict:
    if not settings.stripe_secret_key:
        raise AppError("Stripe is not configured", code="stripe_config", status_code=503)

    stripe.api_key = settings.stripe_secret_key
    customer = session.exec(
        select(BillingCustomer).where(BillingCustomer.organization_id == principal.organization_id)
    ).first()

    if customer is None:
        raise NotFoundError("No billing customer")

    portal = stripe.billing_portal.Session.create(
        customer=customer.stripe_customer_id,
        return_url=f"{settings.frontend_url.rstrip('/')}/settings#billing",
    )
    return {"portal_url": portal["url"]}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, session: SessionDep, settings: SettingsDep) -> dict:

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        raise AppError("Webhook secret not configured", code="stripe_config", status_code=503)
    try:
        constructed = stripe.Webhook.construct_event(
            payload, sig, settings.stripe_webhook_secret
        )
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            "Invalid Stripe signature",
            code="stripe_signature",
            status_code=400,
        ) from exc

    # Newer stripe-python returns StripeObjects; normalize to plain dicts.
    event = constructed.to_dict() if hasattr(constructed, "to_dict") else dict(constructed)
    data_object = event.get("data", {}).get("object") or {}
    if hasattr(data_object, "to_dict"):
        data = data_object.to_dict()
    elif isinstance(data_object, dict):
        data = data_object
    else:
        data = dict(data_object)

    event_id = str(event.get("id") or "")
    etype = str(event.get("type") or "")

    existing = session.exec(
        select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == event_id)
    ).first()

    if existing:
        return {"status": "duplicate"}

    session.add(
        StripeWebhookEvent(
            stripe_event_id=event_id,
            event_type=etype,
            status="processed",
        )
    )

    if etype in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        metadata = data.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = dict(metadata) if metadata else {}
        org_id = metadata.get("organization_id")
        customer_id = data.get("customer")
        if not org_id and customer_id:
            bc = session.exec(
                select(BillingCustomer).where(BillingCustomer.stripe_customer_id == customer_id)
            ).first()
            org_id = str(bc.organization_id) if bc else None
        if org_id:
            sub = session.exec(
                select(Subscription).where(Subscription.organization_id == UUID(str(org_id)))
            ).first()
            if sub is None:
                sub = Subscription(organization_id=UUID(str(org_id)))
            status = data.get("status") or SubscriptionStatus.NONE.value
            if etype.endswith("deleted"):
                status = SubscriptionStatus.CANCELED.value
            sub.status = status
            sub.stripe_subscription_id = data.get("id")
            items = data.get("items") or {}
            if not isinstance(items, dict):
                items = items.to_dict() if hasattr(items, "to_dict") else {}
            item_rows = items.get("data") or []
            if item_rows:
                price = (item_rows[0] or {}).get("price") or {}
                if not isinstance(price, dict):
                    price = price.to_dict() if hasattr(price, "to_dict") else {}
                sub.stripe_price_id = price.get("id")
            if status in {SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value}:
                sub.plan_tier = PlanTier.PRO.value
            elif status == SubscriptionStatus.CANCELED.value:
                sub.plan_tier = PlanTier.FREE.value
            sub.cancel_at_period_end = bool(data.get("cancel_at_period_end"))
            sub.updated_at = utcnow()
            session.add(sub)

    elif etype == "checkout.session.completed":
        metadata = data.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = dict(metadata) if metadata else {}
        org_id = metadata.get("organization_id")
        if org_id:
            sub = session.exec(
                select(Subscription).where(Subscription.organization_id == UUID(str(org_id)))
            ).first()
            if sub is None:
                sub = Subscription(organization_id=UUID(str(org_id)))
            if data.get("mode") == "subscription":
                sub.status = SubscriptionStatus.ACTIVE.value
                sub.plan_tier = PlanTier.PRO.value
                sub.stripe_price_id = settings.stripe_price_id
                sub.stripe_subscription_id = data.get("subscription")
                sub.updated_at = utcnow()
                session.add(sub)

    session.commit()
    return {"status": "ok"}
