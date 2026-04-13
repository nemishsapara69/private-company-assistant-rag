from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.chat import get_current_user
from app.db.session import get_db
from app.models import AuditLog
from app.schemas.admin import AdminMetricsResponse
from app.schemas.auth import UserSession

router = APIRouter()


@router.get("/metrics", response_model=AdminMetricsResponse)
def get_metrics(
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminMetricsResponse:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can view metrics.")

    logs = db.execute(select(AuditLog)).scalars().all()
    module_counter = Counter(log.module for log in logs)

    top_modules = [
        {"module": module, "count": count}
        for module, count in module_counter.most_common(5)
    ]

    return AdminMetricsResponse(
        total_queries=len(logs),
        denied_scope_queries=sum(1 for log in logs if log.authorization_result == "denied_scope"),
        blocked_injection_queries=sum(1 for log in logs if log.authorization_result == "blocked_injection"),
        low_confidence_fallbacks=sum(1 for log in logs if log.authorization_result == "fallback_low_conf"),
        top_modules=top_modules,
    )
