from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    module: str = Field(default="policy")


class Citation(BaseModel):
    document: str
    section: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    confidence: float
    access_scope: str
