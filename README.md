# Private Company Assistant Using RAG

Enterprise-style employee helpdesk and knowledge assistant with role-aware retrieval, citations, and auditability.

## Current Status

Phase 1 and Phase 2 foundation are ready:
- FastAPI backend structure
- Login endpoint with JWT
- Role-based access checks
- Chat endpoint placeholder with source citations format
- SQLite database persistence (users and audit logs)
- Startup data seeding for demo users
- Per-request audit logging for allowed and denied chat calls
- Admin document upload with TXT, PDF, and DOCX parsing
- Chunk storage for later vector search
- Chat retrieval from stored chunks with citations
- Phase 3 semantic retrieval with local Qdrant vector store

## Quick Start

1. Create virtual environment
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Copy environment file:
   - `.env.example` to `.env`
4. Run API:
   - `uvicorn app.main:app --reload`
5. Open API docs:
   - `http://127.0.0.1:8000/docs`

## Demo Credentials

- alice / alice123 (employee)
- bob / bob123 (manager)
- hr_admin / hr123 (hr)
- it_admin / it123 (it)
- super_admin / admin123 (admin)

## API Endpoints

- GET /api/v1/health
- POST /api/v1/auth/login
- POST /api/v1/chat
- POST /api/v1/documents (admin only)
- GET /api/v1/documents (role-filtered listing)
- POST /api/v1/documents/upload (admin only ingestion)
- GET /api/v1/documents/{document_id}/chunks (admin debug)

## Local Database

- Default DB file: `assistant.db`
- Tables created on startup: `users`, `audit_logs`, `documents`, `document_chunks`

## Quick Document Module Test

1. Login as `super_admin` / `admin123`.
2. Authorize in Swagger.
3. Call POST `/api/v1/documents` with sample metadata.
4. Call GET `/api/v1/documents` as admin and as employee to observe role filtering.

## Quick Ingestion Test

1. Login as `super_admin` / `admin123`.
2. Authorize in Swagger.
3. Call POST `/api/v1/documents/upload` with a `.txt`, `.pdf`, or `.docx` file.
4. Confirm the response shows the created document plus `chunk_count` and `extracted_characters`.

## Quick Retrieval Test

1. Login as `hr_admin` / `hr123` and authorize.
2. Call POST `/api/v1/chat` with module `hr` and a leave-related question.
3. Confirm response includes citations from uploaded documents.

## Semantic Retrieval Notes

1. Uploaded chunks are embedded using `sentence-transformers/all-MiniLM-L6-v2`.
2. Vectors are stored in local Qdrant at `qdrant_data/`.
3. Chat uses semantic search first, then keyword fallback if needed.

## Security Controls (Phase 5)

1. Prompt-injection attempts are blocked at chat input validation.
2. Uploaded document text is sanitized before chunking/indexing.
3. Semantic payloads are re-checked for role/module eligibility at retrieval time.
4. Audit logs now include structured outcomes such as `blocked_injection`, `denied_scope`, and `fallback_low_conf`.

## Security Regression Tests

Run:

`python -m pytest tests/test_phase5_security.py -q`

## Workflow Automation (Phase 7)

1. Document approval workflow endpoints:
   - `POST /api/v1/workflows/document-approvals`
   - `POST /api/v1/workflows/document-approvals/{approval_id}/decision`
2. Ticket workflow for unresolved questions:
   - Auto-created on low-confidence chat fallback
   - Manual creation: `POST /api/v1/workflows/tickets`
3. Policy notification workflow:
   - `POST /api/v1/workflows/policy-notifications`

Phase 7 workflow tests:

`python -m pytest tests/test_phase7_workflows.py -q`

## Learning Path

Read `docs/STEP_BY_STEP_PLAN.md` and implement phase by phase.
