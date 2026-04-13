from __future__ import annotations

from qdrant_client.models import PointStruct

from app.models import Document, DocumentChunk
from app.services.embedding_service import embed_texts
from app.services.vector_store import ensure_collection, upsert_points


def build_point_id(document_id: int, chunk_index: int) -> int:
    return document_id * 100000 + chunk_index


def index_document_chunks(
    document: Document,
    chunk_records: list[DocumentChunk],
    allowed_roles: list[str],
) -> int:
    if not chunk_records:
        return 0

    chunk_texts = [chunk.content for chunk in chunk_records]
    vectors = embed_texts(chunk_texts)
    if not vectors:
        return 0

    ensure_collection(vector_size=len(vectors[0]))

    points: list[PointStruct] = []
    for chunk, vector in zip(chunk_records, vectors):
        points.append(
            PointStruct(
                id=build_point_id(document.id, chunk.chunk_index),
                vector=vector,
                payload={
                    "document_id": document.id,
                    "title": document.title,
                    "department": document.department,
                    "doc_type": document.doc_type,
                    "sensitivity": document.sensitivity,
                    "owner": document.owner,
                    "allowed_roles": allowed_roles,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "source_path": document.source_path,
                },
            )
        )

    upsert_points(points)
    return len(points)
