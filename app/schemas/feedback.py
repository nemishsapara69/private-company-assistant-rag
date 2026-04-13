from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    module: str = Field(default="policy", min_length=2, max_length=100)
    question: str = Field(min_length=3, max_length=2000)
    answer: str = Field(min_length=3, max_length=6000)
    citations: list[str] = Field(default_factory=list)
    helpful: bool
    comment: str = Field(default="", max_length=1000)


class FeedbackResponse(BaseModel):
    id: int
    username: str
    role: str
    module: str
    helpful: bool
    comment: str
    created_at: datetime
