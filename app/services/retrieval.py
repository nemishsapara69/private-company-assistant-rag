import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk
from app.schemas.chat import Citation


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


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
        excerpt = chunk.content[:280].strip()
        answer_parts.append(f"- {excerpt}")
        citations.append(Citation(document=doc.title, section=f"Chunk {chunk.chunk_index}"))

    confidence = min(0.95, 0.45 + (total_score / (total_score + 6)))
    answer = "Based on authorized documents:\n" + "\n".join(answer_parts)
    return answer, citations, confidence, access_scope
