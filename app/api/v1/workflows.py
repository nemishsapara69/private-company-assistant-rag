from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.chat import get_current_user
from app.db.session import get_db
from app.models import Document, DocumentApprovalRequest, PolicyNotification, SupportTicket
from app.schemas.auth import UserSession
from app.schemas.workflow import (
    DocumentApprovalCreateRequest,
    DocumentApprovalDecisionRequest,
    DocumentApprovalResponse,
    PolicyNotificationCreateRequest,
    PolicyNotificationResponse,
    TicketCreateRequest,
    TicketResponse,
)
from app.services.workflow_service import create_support_ticket, join_roles, normalize_roles

router = APIRouter()


def _admin_only(user: UserSession) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can perform this action.")


@router.post("/document-approvals", response_model=DocumentApprovalResponse)
def create_document_approval(
    payload: DocumentApprovalCreateRequest,
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentApprovalResponse:
    _admin_only(user)

    doc = db.execute(select(Document).where(Document.id == payload.document_id)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    row = DocumentApprovalRequest(
        document_id=payload.document_id,
        requested_by=user.username,
        reviewer=payload.reviewer,
        status="pending",
        note=payload.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return DocumentApprovalResponse(
        id=row.id,
        document_id=row.document_id,
        requested_by=row.requested_by,
        reviewer=row.reviewer,
        status=row.status,
        note=row.note,
        decision_comment=row.decision_comment,
        decided_by=row.decided_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/document-approvals/{approval_id}/decision", response_model=DocumentApprovalResponse)
def decide_document_approval(
    approval_id: int,
    payload: DocumentApprovalDecisionRequest,
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentApprovalResponse:
    _admin_only(user)

    row = db.execute(select(DocumentApprovalRequest).where(DocumentApprovalRequest.id == approval_id)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found.")

    row.status = "approved" if payload.approve else "rejected"
    row.decision_comment = payload.comment
    row.decided_by = user.username
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)

    return DocumentApprovalResponse(
        id=row.id,
        document_id=row.document_id,
        requested_by=row.requested_by,
        reviewer=row.reviewer,
        status=row.status,
        note=row.note,
        decision_comment=row.decision_comment,
        decided_by=row.decided_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/document-approvals", response_model=list[DocumentApprovalResponse])
def list_document_approvals(
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentApprovalResponse]:
    _admin_only(user)
    rows = db.execute(select(DocumentApprovalRequest).order_by(DocumentApprovalRequest.created_at.desc())).scalars().all()
    return [
        DocumentApprovalResponse(
            id=row.id,
            document_id=row.document_id,
            requested_by=row.requested_by,
            reviewer=row.reviewer,
            status=row.status,
            note=row.note,
            decision_comment=row.decision_comment,
            decided_by=row.decided_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.post("/tickets", response_model=TicketResponse)
def create_ticket_manual(
    payload: TicketCreateRequest,
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TicketResponse:
    row = create_support_ticket(
        db=db,
        username=user.username,
        role=user.role,
        module=payload.module,
        question=payload.question,
        reason=payload.reason,
        auto_created=False,
    )
    return TicketResponse(
        id=row.id,
        username=row.username,
        role=row.role,
        module=row.module,
        reason=row.reason,
        status=row.status,
        auto_created=row.auto_created,
        created_at=row.created_at,
    )


@router.get("/tickets", response_model=list[TicketResponse])
def list_tickets(
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TicketResponse]:
    _admin_only(user)
    rows = db.execute(select(SupportTicket).order_by(SupportTicket.created_at.desc())).scalars().all()
    return [
        TicketResponse(
            id=row.id,
            username=row.username,
            role=row.role,
            module=row.module,
            reason=row.reason,
            status=row.status,
            auto_created=row.auto_created,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/policy-notifications", response_model=PolicyNotificationResponse)
def create_policy_notification(
    payload: PolicyNotificationCreateRequest,
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PolicyNotificationResponse:
    _admin_only(user)

    doc = db.execute(select(Document).where(Document.id == payload.document_id)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    row = PolicyNotification(
        document_id=payload.document_id,
        message=payload.message,
        target_roles=join_roles(payload.target_roles),
        status="sent",
        sent_by=user.username,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return PolicyNotificationResponse(
        id=row.id,
        document_id=row.document_id,
        message=row.message,
        target_roles=normalize_roles(row.target_roles),
        status=row.status,
        sent_by=row.sent_by,
        created_at=row.created_at,
    )


@router.get("/policy-notifications", response_model=list[PolicyNotificationResponse])
def list_policy_notifications(
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PolicyNotificationResponse]:
    _admin_only(user)
    rows = db.execute(select(PolicyNotification).order_by(PolicyNotification.created_at.desc())).scalars().all()
    return [
        PolicyNotificationResponse(
            id=row.id,
            document_id=row.document_id,
            message=row.message,
            target_roles=normalize_roles(row.target_roles),
            status=row.status,
            sent_by=row.sent_by,
            created_at=row.created_at,
        )
        for row in rows
    ]