from __future__ import annotations

import re
from typing import Any


_PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?instructions",
    r"reveal\s+(the\s+)?(system|developer)\s+prompt",
    r"bypass\s+(security|authorization|rbac)",
    r"act\s+as\s+admin",
    r"jailbreak",
    r"override\s+polic(y|ies)",
]


def is_prompt_injection_attempt(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if not normalized:
        return False
    return any(re.search(pattern, normalized) for pattern in _PROMPT_INJECTION_PATTERNS)


def sanitize_text_for_retrieval(text: str) -> str:
    if not text:
        return ""

    sanitized = text.replace("\x00", " ")
    sanitized = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", sanitized)

    # Remove common in-document instruction lines that can poison retrieval context.
    lines = []
    for line in sanitized.splitlines():
        lowered = line.strip().lower()
        if is_prompt_injection_attempt(lowered):
            continue
        lines.append(line)

    merged = "\n".join(lines)
    merged = re.sub(r"\s+", " ", merged)
    return merged.strip()


def payload_role_allowed(payload: dict[str, Any], role: str) -> bool:
    raw_roles = payload.get("allowed_roles", [])
    if isinstance(raw_roles, str):
        roles = [item.strip() for item in raw_roles.split(",") if item.strip()]
    elif isinstance(raw_roles, list):
        roles = [str(item).strip() for item in raw_roles if str(item).strip()]
    else:
        roles = []
    if role == "admin":
        return True
    return role in roles or "admin" in roles


def payload_matches_module(payload: dict[str, Any], module: str) -> bool:
    normalized = (module or "policy").lower()
    department = str(payload.get("department", "")).lower()
    doc_type = str(payload.get("doc_type", "")).lower()

    if normalized == "policy":
        return doc_type == "policy"
    if normalized == "hr":
        return department == "hr"
    if normalized == "it":
        return department == "it"
    if normalized == "manager":
        return department in {"operations", "management", "manager"}
    return True