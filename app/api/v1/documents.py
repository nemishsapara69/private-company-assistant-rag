from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.chat import get_current_user
from app.db.session import get_db
from app.models import Document
from app.schemas.auth import UserSession
from app.schemas.document import DocumentCreateRequest, DocumentListResponse, DocumentResponse

router = APIRouter()


def parse_roles(role_csv: str) -> list[str]:
    return [role.strip() for role in role_csv.split(",") if role.strip()]


@router.post("", response_model=DocumentResponse)
def create_document(
    payload: DocumentCreateRequest,
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can create documents.")

    doc = Document(
        title=payload.title,
        department=payload.department,
        doc_type=payload.doc_type,
        sensitivity=payload.sensitivity,
        owner=payload.owner,
        allowed_roles=",".join(payload.allowed_roles),
        source_path=payload.source_path,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        department=doc.department,
        doc_type=doc.doc_type,
        sensitivity=doc.sensitivity,
        owner=doc.owner,
        allowed_roles=parse_roles(doc.allowed_roles),
        source_path=doc.source_path,
        created_at=doc.created_at,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    docs = db.execute(select(Document).order_by(Document.created_at.desc())).scalars().all()

    visible_docs = []
    for doc in docs:
        roles = parse_roles(doc.allowed_roles)
        if user.role in roles or user.role == "admin":
            visible_docs.append(
                DocumentResponse(
                    id=doc.id,
                    title=doc.title,
                    department=doc.department,
                    doc_type=doc.doc_type,
                    sensitivity=doc.sensitivity,
                    owner=doc.owner,
                    allowed_roles=roles,
                    source_path=doc.source_path,
                    created_at=doc.created_at,
                )
            )

    return DocumentListResponse(documents=visible_docs)
