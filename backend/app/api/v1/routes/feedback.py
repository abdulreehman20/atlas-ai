"""Answer feedback routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import PrincipalDep, SessionDep
from app.db.models.feedback import Feedback
from app.schemas.chat import FeedbackRequest, FeedbackResponse

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse, tags=["chat"])
def create_feedback(
    body: FeedbackRequest,
    principal: PrincipalDep,
    session: SessionDep,
) -> FeedbackResponse:
    row = Feedback(
        workspace_id=principal.workspace_id,
        user_id=principal.user_id,
        conversation_id=body.conversation_id,
        message_id=body.message_id,
        rating=body.rating,
        comment=body.comment,
    )

    session.add(row)
    session.commit()
    session.refresh(row)
    return FeedbackResponse(id=row.id, rating=row.rating)
