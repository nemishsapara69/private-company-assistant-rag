from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    department: str = Field(min_length=2, max_length=100)
    doc_type: str = Field(min_length=2, max_length=50)
    sensitivity: str = Field(default="internal", min_length=2, max_length=50)
    owner: str = Field(min_length=2, max_length=100)
    allowed_roles: list[str] = Field(default_factory=lambda: ["employee", "manager", "hr", "it", "admin"])
    source_path: str = Field(default="", max_length=500)


class DocumentResponse(BaseModel):
    id: int
    title: str
    department: str
    doc_type: str
    sensitivity: str
    owner: str
    allowed_roles: list[str]
    source_path: str
    created_at: datetime


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
