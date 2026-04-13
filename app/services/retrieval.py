import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk
from app.schemas.chat import Citation
from app.services.embedding_service import embed_query
from app.services.security_guardrails import payload_matches_module, payload_role_allowed
from app.services.vector_store import semantic_search


@dataclass
class _Candidate:
    document_id: int
    title: str
    chunk_index: int
    content: str
    source_page: str = ""
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    rerank_score: float = 0.0

    @property
    def key(self) -> tuple[int, int]:
        return (self.document_id, self.chunk_index)


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


def _sentence_match_score(sentence: str, question: str) -> int:
    query_lower = question.lower()
    sentence_lower = sentence.lower()

    query_tokens = _tokenize(question)
    sentence_tokens = _tokenize(sentence)
    overlap = len(query_tokens.intersection(sentence_tokens))

    # Small domain boosts improve ranking for intent-heavy prompts.
    if "password" in query_lower and "password" in sentence_lower:
        overlap += 2
    if any(term in query_lower for term in ("minimum", "length", "at least")):
        if any(term in sentence_lower for term in ("minimum", "at least", "character", "characters")):
            overlap += 2
    if "vpn" in query_lower and "vpn" in sentence_lower:
        overlap += 2
    if "mfa" in query_lower and ("mfa" in sentence_lower or "multi-factor" in sentence_lower):
        overlap += 2

    return overlap


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


def _best_snippet(text: str, question: str, max_sentences: int = 2, max_chars: int = 420) -> str:
    sentences = _sentence_split(text)
    if not sentences:
        return text[:max_chars].strip()

    query_tokens = _tokenize(question)
    scored: list[tuple[int, int, str]] = []
    for idx, sentence in enumerate(sentences):
        overlap = _sentence_match_score(sentence, question)
        scored.append((overlap, -idx, sentence))

    scored.sort(reverse=True)
    chosen = [item[2] for item in scored[:max_sentences] if item[0] > 0]
    if not chosen:
        chosen = sentences[:max_sentences]

    snippet = " ".join(chosen).strip()
    return snippet[:max_chars].strip()


def _citation_section(chunk_index: int, source_page: str) -> str:
    if source_page:
        return f"Chunk {chunk_index} (Page {source_page})"
    return f"Chunk {chunk_index}"


def _collect_keyword_candidates(question: str, module: str, role: str, db: Session) -> dict[tuple[int, int], _Candidate]:
    user_tokens = _tokenize(question)
    if not user_tokens:
        return {}

    docs = db.execute(select(Document)).scalars().all()
    candidates: dict[tuple[int, int], _Candidate] = {}

    for doc in docs:
        roles = [item.strip() for item in doc.allowed_roles.split(",") if item.strip()]
        if role != "admin" and role not in roles:
            continue
        if not _doc_matches_module(doc, module):
            continue

        chunks = db.execute(select(DocumentChunk).where(DocumentChunk.document_id == doc.id)).scalars().all()
        for chunk in chunks:
            chunk_tokens = _tokenize(chunk.content)
            overlap_count = len(user_tokens.intersection(chunk_tokens))
            if overlap_count == 0:
                continue

            lexical_score = overlap_count / max(1, len(user_tokens))
            key = (doc.id, chunk.chunk_index)
            current = candidates.get(key)
            if current is None:
                candidates[key] = _Candidate(
                    document_id=doc.id,
                    title=doc.title,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    source_page=chunk.source_page or "",
                    lexical_score=lexical_score,
                )
            else:
                current.lexical_score = max(current.lexical_score, lexical_score)

    return candidates


def _merge_semantic_hits(question: str, module: str, role: str) -> dict[tuple[int, int], _Candidate]:
    candidates: dict[tuple[int, int], _Candidate] = {}
    try:
        query_vector = embed_query(question)
        hits = semantic_search(query_vector=query_vector, role=role, module=module, limit=12)
    except Exception:
        hits = []

    for hit in hits:
        payload = hit.payload or {}
        if not payload_role_allowed(payload, role):
            continue
        if not payload_matches_module(payload, module):
            continue
        document_id = int(payload.get("document_id", 0) or 0)
        chunk_index = int(payload.get("chunk_index", 0) or 0)
        if document_id <= 0:
            continue
        key = (document_id, chunk_index)
        semantic_score = max(0.0, float(hit.score))
        content = str(payload.get("content", "")).strip()
        if not content:
            continue

        current = candidates.get(key)
        if current is None:
            candidates[key] = _Candidate(
                document_id=document_id,
                title=str(payload.get("title", "Untitled Document")),
                chunk_index=chunk_index,
                content=content,
                source_page=str(payload.get("source_page", "") or ""),
                semantic_score=semantic_score,
            )
        else:
            current.semantic_score = max(current.semantic_score, semantic_score)

    return candidates


def retrieve_answer(question: str, module: str, role: str, db: Session) -> tuple[str, list[Citation], float, str]:
    access_scope = _module_to_scope(module)
    semantic_candidates = _merge_semantic_hits(question=question, module=module, role=role)
    keyword_candidates = _collect_keyword_candidates(question=question, module=module, role=role, db=db)

    merged: dict[tuple[int, int], _Candidate] = {}
    for key, candidate in keyword_candidates.items():
        merged[key] = candidate
    for key, candidate in semantic_candidates.items():
        existing = merged.get(key)
        if existing is None:
            merged[key] = candidate
        else:
            existing.semantic_score = max(existing.semantic_score, candidate.semantic_score)
            if not existing.content:
                existing.content = candidate.content
            if not existing.title:
                existing.title = candidate.title
            if not existing.source_page:
                existing.source_page = candidate.source_page

    if not merged:
        return (
            "I do not know based on the authorized knowledge sources right now.",
            [],
            0.2,
            access_scope,
        )

    reranked: list[tuple[float, _Candidate, str]] = []
    for candidate in merged.values():
        snippet = _best_snippet(candidate.content, question=question)
        candidate.rerank_score = min(1.0, _sentence_match_score(snippet, question) / 10.0)
        combined = (0.60 * candidate.semantic_score) + (0.25 * candidate.lexical_score) + (0.15 * candidate.rerank_score)
        reranked.append((combined, candidate, snippet))

    reranked.sort(key=lambda item: (item[0], item[1].semantic_score, item[1].lexical_score), reverse=True)

    selected = reranked[:3]
    top_combined = selected[0][0]
    if top_combined < 0.22:
        return (
            "I do not know based on the authorized knowledge sources right now.",
            [],
            0.2,
            access_scope,
        )

    answer_parts: list[str] = []
    citations: list[Citation] = []
    seen_snippets: set[str] = set()
    for _, candidate, snippet in selected:
        normalized_snippet = snippet.lower()
        if normalized_snippet in seen_snippets:
            continue
        seen_snippets.add(normalized_snippet)
        answer_parts.append(f"- {snippet}")
        citations.append(
            Citation(
                document=candidate.title,
                section=_citation_section(candidate.chunk_index, candidate.source_page),
            )
        )

    if not answer_parts:
        return (
            "I do not know based on the authorized knowledge sources right now.",
            [],
            0.2,
            access_scope,
        )

    confidence = min(0.95, max(0.35, 0.2 + (0.75 * min(1.0, top_combined))))
    answer = "Based on authorized hybrid matches:\n" + "\n".join(answer_parts)
    return answer, citations, confidence, access_scope
