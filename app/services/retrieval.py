import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk
from app.schemas.chat import Citation
from app.services.embedding_service import embed_query
from app.services.vector_store import semantic_search


def _normalize_token(token: str) -> str:
    value = token.lower()
    for suffix in ("ing", "ed", "es", "s"):
        if len(value) > 4 and value.endswith(suffix):
            value = value[: -len(suffix)]
            break
    if len(value) > 4 and value.endswith("e"):
        value = value[:-1]
    return value


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {_normalize_token(token) for token in tokens if token}


def _sentence_split(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part and part.strip()]


def _best_snippet(text: str, question: str, max_sentences: int = 2, max_chars: int = 420) -> str:
    sentences = _sentence_split(text)
    if not sentences:
        return text[:max_chars].strip()

    query_tokens = _tokenize(question)
    scored: list[tuple[int, int, str]] = []
    for idx, sentence in enumerate(sentences):
        sentence_tokens = _tokenize(sentence)
        overlap = len(query_tokens.intersection(sentence_tokens))
        scored.append((overlap, -idx, sentence))

    scored.sort(reverse=True)
    chosen = [item[2] for item in scored[:max_sentences] if item[0] > 0]
    if not chosen:
        chosen = sentences[:max_sentences]

    snippet = " ".join(chosen).strip()
    return snippet[:max_chars].strip()


def _module_to_scope(module: str) -> str:
    scope_map = {
        "hr": "hr_docs",
        "it": "it_docs",
        "policy": "public_policies",
        "manager": "manager_policies",
    }
    return scope_map.get(module, "public_policies")


def _doc_matches_module(doc: Document, module: str) -> bool:
    normalized_module = module.lower()
    if normalized_module == "policy":
        return doc.doc_type.lower() == "policy"
    if normalized_module == "hr":
        return doc.department.lower() == "hr"
    if normalized_module == "it":
        return doc.department.lower() == "it"
    if normalized_module == "manager":
        return doc.department.lower() in {"operations", "management", "manager"}
    return True


def retrieve_answer(question: str, module: str, role: str, db: Session) -> tuple[str, list[Citation], float, str]:
    access_scope = _module_to_scope(module)
    user_tokens = _tokenize(question)

    # Phase 3 primary path: semantic vector retrieval with role/module filtering.
    try:
        query_vector = embed_query(question)
        hits = semantic_search(query_vector=query_vector, role=role, module=module, limit=3)
    except Exception:
        hits = []

    if hits:
        semantic_parts = []
        semantic_citations = []
        top_score = max(item.score for item in hits)

        for hit in hits:
            payload = hit.payload or {}
            content = str(payload.get("content", "")).strip()
            if not content:
                continue
            snippet = _best_snippet(content, question=question)
            semantic_parts.append(f"- {snippet}")
            semantic_citations.append(
                Citation(
                    document=str(payload.get("title", "Untitled Document")),
                    section=f"Chunk {payload.get('chunk_index', '?')}",
                )
            )

        if semantic_parts:
            confidence = max(0.45, min(0.98, float(top_score)))
            answer = "Based on authorized semantic matches:\n" + "\n".join(semantic_parts)
            return answer, semantic_citations, confidence, access_scope

    docs = db.execute(select(Document)).scalars().all()
    candidate_docs = []
    for doc in docs:
        roles = [item.strip() for item in doc.allowed_roles.split(",") if item.strip()]
        if role != "admin" and role not in roles:
            continue
        if not _doc_matches_module(doc, module):
            continue
        candidate_docs.append(doc)

    scored_chunks: list[tuple[int, Document, DocumentChunk]] = []
    for doc in candidate_docs:
        chunks = db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        ).scalars().all()
        for chunk in chunks:
            chunk_tokens = _tokenize(chunk.content)
            score = len(user_tokens.intersection(chunk_tokens))
            if score > 0:
                scored_chunks.append((score, doc, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    top_chunks = scored_chunks[:3]

    if not top_chunks:
        return (
            "I do not know based on the authorized knowledge sources right now.",
            [],
            0.2,
            access_scope,
        )

    answer_parts = []
    citations = []
    total_score = 0
    for score, doc, chunk in top_chunks:
        total_score += score
        excerpt = _best_snippet(chunk.content, question=question)
        answer_parts.append(f"- {excerpt}")
        citations.append(Citation(document=doc.title, section=f"Chunk {chunk.chunk_index}"))

    confidence = min(0.95, 0.45 + (total_score / (total_score + 6)))
    answer = "Based on authorized documents:\n" + "\n".join(answer_parts)
    return answer, citations, confidence, access_scope
