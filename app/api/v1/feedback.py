import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.chat import get_current_user
from app.db.session import get_db
from app.models import Feedback
from app.schemas.auth import UserSession
from app.schemas.feedback import FeedbackCreateRequest, FeedbackResponse

router = APIRouter()


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackCreateRequest,
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    if payload.module.lower() not in {"policy", "hr", "it", "manager"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid module value.")

    row = Feedback(
        username=user.username,
        role=user.role,
        module=payload.module,
        question=payload.question,
        answer=payload.answer,
        citations=json.dumps(payload.citations),
        helpful=payload.helpful,
        comment=payload.comment,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return FeedbackResponse(
        id=row.id,
        username=row.username,
        role=row.role,
        module=row.module,
        helpful=row.helpful,
        comment=row.comment,
        created_at=row.created_at,
    )
