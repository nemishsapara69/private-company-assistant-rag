from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.rbac import enforce_scope
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import AuditLog
from app.schemas.auth import UserSession
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.retrieval import retrieve_answer

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> UserSession:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = credentials.credentials.strip()
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        role = payload.get("role")
        if not username or not role:
            raise ValueError("Invalid token payload")
        return UserSession(username=username, role=role)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


@router.post("", response_model=ChatResponse)
def chat(
    query: ChatRequest,
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    answer, citations, confidence, scope = retrieve_answer(
        question=query.question,
        module=query.module,
        role=user.role,
    )

    try:
        enforce_scope(user.role, scope)
        auth_result = "allowed"
    except HTTPException:
        db.add(
            AuditLog(
                username=user.username,
                role=user.role,
                question=query.question,
                module=query.module,
                access_scope=scope,
                authorization_result="denied",
                confidence=confidence,
                citations="",
            )
        )
        db.commit()
        raise

    if confidence < 0.4:
        answer = "I do not know based on the authorized knowledge sources right now."
        citations = []

    citation_text = " | ".join([f"{c.document}::{c.section}" for c in citations])
    db.add(
        AuditLog(
            username=user.username,
            role=user.role,
            question=query.question,
            module=query.module,
            access_scope=scope,
            authorization_result=auth_result,
            confidence=confidence,
            citations=citation_text,
        )
    )
    db.commit()

    return ChatResponse(
        answer=answer,
        citations=citations,
        confidence=confidence,
        access_scope=scope,
    )
