from __future__ import annotations

from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchAny, MatchValue, PointStruct, VectorParams

from app.core.config import settings


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(path=settings.qdrant_path)


def ensure_collection(vector_size: int) -> None:
    client = get_qdrant_client()
    collections = client.get_collections().collections
    collection_names = {item.name for item in collections}
    if settings.qdrant_collection not in collection_names:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def upsert_points(points: list[PointStruct]) -> None:
    if not points:
        return
    client = get_qdrant_client()
    client.upsert(collection_name=settings.qdrant_collection, points=points)


def _module_filter_conditions(module: str) -> list[FieldCondition]:
    normalized = module.lower()
    if normalized == "policy":
        return [FieldCondition(key="doc_type", match=MatchValue(value="policy"))]
    if normalized == "hr":
        return [FieldCondition(key="department", match=MatchValue(value="hr"))]
    if normalized == "it":
        return [FieldCondition(key="department", match=MatchValue(value="it"))]
    if normalized == "manager":
        return [FieldCondition(key="department", match=MatchAny(any=["manager", "management", "operations"]))]
    return []


def semantic_search(query_vector: list[float], role: str, module: str, limit: int = 5):
    client = get_qdrant_client()
    role_condition = FieldCondition(key="allowed_roles", match=MatchAny(any=[role, "admin"]))
    conditions = [role_condition] + _module_filter_conditions(module)

    return client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        query_filter=Filter(must=conditions),
        limit=limit,
        with_payload=True,
    )
