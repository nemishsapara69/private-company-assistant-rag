import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.chat import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import Document, DocumentChunk
from app.schemas.auth import UserSession
from app.schemas.chunk_debug import ChunkPreview, DocumentChunkDebugResponse
from app.schemas.document import DocumentCreateRequest, DocumentListResponse, DocumentResponse
from app.schemas.ingestion import IngestResponse
from app.services.document_processing import SUPPORTED_EXTENSIONS, chunk_text, extract_text_from_file

router = APIRouter()


def parse_roles(role_csv: str) -> list[str]:
    return [role.strip() for role in role_csv.split(",") if role.strip()]


def parse_allowed_roles_input(raw_value: str) -> list[str]:
    # Swagger multipart fields are easy to mistype; accept JSON array or csv.
    text = (raw_value or "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="allowed_roles is required.")

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            roles = [str(item).strip() for item in parsed if str(item).strip()]
            if roles:
                return roles
    except ValueError:
        pass

    normalized = text.strip("[]")
    parts = normalized.replace(";", ",").split(",")
    roles = [part.strip().strip('"').strip("'") for part in parts if part.strip()]
    if roles:
        return roles

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="allowed_roles must be a JSON array or comma-separated list.")


def build_document_response(doc: Document) -> DocumentResponse:
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

    return build_document_response(doc)


@router.post("/upload", response_model=IngestResponse)
async def upload_document(
    title: str = Form(..., min_length=3, max_length=255),
    department: str = Form(..., min_length=2, max_length=100),
    doc_type: str = Form(..., min_length=2, max_length=50),
    sensitivity: str = Form(default="internal", min_length=2, max_length=50),
    owner: str = Form(..., min_length=2, max_length=100),
    allowed_roles: str = Form(default='["employee", "manager", "hr", "it", "admin"]'),
    file: UploadFile = File(...),
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IngestResponse:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can upload documents.")

    filename = file.filename or "uploaded_file"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type.")

    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{suffix}"
    stored_path = upload_root / stored_name

    file_bytes = await file.read()
    stored_path.write_bytes(file_bytes)

    extracted_text = extract_text_from_file(stored_path)
    chunks = chunk_text(extracted_text)

    parsed_allowed_roles = parse_allowed_roles_input(allowed_roles)

    document = Document(
        title=title,
        department=department,
        doc_type=doc_type,
        sensitivity=sensitivity,
        owner=owner,
        allowed_roles=",".join(str(role) for role in parsed_allowed_roles),
        source_path=str(stored_path).replace("\\", "/"),
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    for index, chunk in enumerate(chunks):
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                source_page="",
                metadata_json=json.dumps(
                    {
                        "title": title,
                        "department": department,
                        "doc_type": doc_type,
                        "sensitivity": sensitivity,
                        "owner": owner,
                        "source_file": filename,
                    }
                ),
            )
        )

    db.commit()

    return IngestResponse(
        document=build_document_response(document),
        chunk_count=len(chunks),
        extracted_characters=len(extracted_text),
        source_file=filename,
        created_at=document.created_at,
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
            visible_docs.append(build_document_response(doc))

    return DocumentListResponse(documents=visible_docs)


@router.get("/{document_id}/chunks", response_model=DocumentChunkDebugResponse)
def get_document_chunks_debug(
    document_id: int,
    user: UserSession = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentChunkDebugResponse:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can inspect chunks.")

    document = db.execute(select(Document).where(Document.id == document_id)).scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    chunks = db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index.asc())
    ).scalars().all()

    previews = [
        ChunkPreview(chunk_index=chunk.chunk_index, preview=chunk.content[:180])
        for chunk in chunks[:5]
    ]

    return DocumentChunkDebugResponse(
        document_id=document.id,
        title=document.title,
        chunk_count=len(chunks),
        previews=previews,
    )
