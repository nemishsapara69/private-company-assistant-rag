from app.schemas.chat import Citation


# Placeholder retrieval service for Phase 1.
# Later you will replace this with vector DB + hybrid retrieval.
def retrieve_answer(question: str, module: str, role: str) -> tuple[str, list[Citation], float, str]:
    scope_map = {
        "hr": "hr_docs",
        "it": "it_docs",
        "policy": "public_policies",
        "manager": "manager_policies",
    }

    access_scope = scope_map.get(module, "public_policies")

    answer = (
        f"Phase 1 demo response for module '{module}'. "
        f"You asked: '{question}'. "
        "In Phase 2, this answer will come from RAG retrieval over approved documents."
    )

    citations = [
        Citation(document="Employee_Handbook_v1.pdf", section="Section 2.1"),
        Citation(document="IT_Onboarding_Guide.pdf", section="Page 4"),
    ]

    confidence = 0.62
    return answer, citations, confidence, access_scope
