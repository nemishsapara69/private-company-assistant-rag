from __future__ import annotations

from functools import lru_cache

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        raise RuntimeError(
            "sentence-transformers is not installed. Run pip install -r requirements.txt"
        ) from exc

    return SentenceTransformer(settings.embedding_model_name)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [vector.tolist() for vector in vectors]


def embed_query(text: str) -> list[float]:
    model = get_embedding_model()
    vector = model.encode([text], normalize_embeddings=True)[0]
    return vector.tolist()
