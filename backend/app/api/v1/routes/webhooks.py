# """External webhook receivers."""

# DELETE -- This is not in use. Live Stripe webhook is inline in billing.py
# (POST /api/v1/billing/webhooks/stripe). Not mounted in router.py.

# from __future__ import annotations

# from fastapi import APIRouter, Header, Request
# from pydantic import BaseModel

# from app.api.deps import SessionDep, SettingsDep
# from app.services import billing as billing_service

# router = APIRouter(prefix="/webhooks")


# class WebhookAck(BaseModel):
#     status: str
#     event_id: str


# @router.post("/stripe", response_model=WebhookAck)
# async def stripe_webhook(
#     request: Request,
#     session: SessionDep,
#     settings: SettingsDep,
#     stripe_signature: str = Header(alias="Stripe-Signature"),
# ) -> WebhookAck:
#     payload = await request.body()
#     event = billing_service.process_stripe_webhook(
#         session,
#         settings,
#         payload=payload,
#         signature=stripe_signature,
#     )
#     return WebhookAck(status=event.status, event_id=event.stripe_event_id)
