"""Aggregate v1 API router."""

from fastapi import APIRouter

from app.api.v1.routes import (
    approvals,
    auth,
    billing,
    chat,
    conversations,
    documents,
    feedback,
    ingestion,
    me,
    memory,
    usage,
    workspaces,
)

api_router = APIRouter()

api_router.include_router(me.router)
api_router.include_router(auth.router)
api_router.include_router(workspaces.router)
api_router.include_router(documents.router)
api_router.include_router(ingestion.router)
api_router.include_router(conversations.router)
api_router.include_router(chat.router)
api_router.include_router(feedback.router)
api_router.include_router(approvals.router)
api_router.include_router(memory.router)
api_router.include_router(billing.router)
api_router.include_router(usage.router)
