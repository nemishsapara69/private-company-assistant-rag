from datetime import datetime

from pydantic import BaseModel

from app.schemas.document import DocumentResponse


class IngestResponse(BaseModel):
    document: DocumentResponse
    chunk_count: int
    indexed_chunks: int
    extracted_characters: int
    source_file: str
    created_at: datetime
