from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import SupportTicket


def normalize_roles(value: list[str] | str) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def join_roles(value: list[str] | str) -> str:
    return ",".join(normalize_roles(value))


def create_support_ticket(
    db: Session,
    username: str,
    role: str,
    module: str,
    question: str,
    reason: str,
    auto_created: bool,
) -> SupportTicket:
    ticket = SupportTicket(
        username=username,
        role=role,
        module=module,
        question=question,
        reason=reason,
        status="open",
        auto_created=auto_created,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket