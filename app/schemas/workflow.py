from datetime import datetime

from pydantic import BaseModel, Field


class DocumentApprovalCreateRequest(BaseModel):
    document_id: int
    reviewer: str = Field(min_length=2, max_length=100)
    note: str = Field(default="", max_length=1000)


class DocumentApprovalDecisionRequest(BaseModel):
    approve: bool
    comment: str = Field(default="", max_length=1000)


class DocumentApprovalResponse(BaseModel):
    id: int
    document_id: int
    requested_by: str
    reviewer: str
    status: str
    note: str
    decision_comment: str
    decided_by: str
    created_at: datetime
    updated_at: datetime


class TicketCreateRequest(BaseModel):
    module: str = Field(default="policy", min_length=2, max_length=100)
    question: str = Field(min_length=3, max_length=2000)
    reason: str = Field(default="manual_request", min_length=3, max_length=100)


class TicketResponse(BaseModel):
    id: int
    username: str
    role: str
    module: str
    reason: str
    status: str
    auto_created: bool
    created_at: datetime


class PolicyNotificationCreateRequest(BaseModel):
    document_id: int
    message: str = Field(min_length=3, max_length=2000)
    target_roles: list[str] = Field(default_factory=lambda: ["employee", "manager", "hr", "it", "admin"])


class PolicyNotificationResponse(BaseModel):
    id: int
    document_id: int
    message: str
    target_roles: list[str]
    status: str
    sent_by: str
    created_at: datetime