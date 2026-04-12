from pydantic import BaseModel


class ChunkPreview(BaseModel):
    chunk_index: int
    preview: str


class DocumentChunkDebugResponse(BaseModel):
    document_id: int
    title: str
    chunk_count: int
    previews: list[ChunkPreview]
