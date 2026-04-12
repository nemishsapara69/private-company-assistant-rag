# Step-by-Step Implementation Plan

This plan is designed so you build and learn in parallel.

## Phase 1: Foundation (Done)

Goal:
- Get backend running with authentication and role checks.

Checklist:
- [x] Project structure
- [x] FastAPI app setup
- [x] Login endpoint
- [x] JWT token creation
- [x] Role-based access guard
- [x] Chat API contract with citations

What you should do now:
1. Run the API locally.
2. Test login in Swagger.
3. Use token to call chat endpoint.
4. Try role-based denial by choosing an unauthorized module.

## Phase 2: Real Data and Persistence

Goal:
- Replace in-memory demo users and placeholder retrieval.

Tasks:
1. Add PostgreSQL (users, roles, documents, audit logs).
2. Add SQLAlchemy models and Alembic migrations.
3. Replace fake users with DB users.
4. Save each chat request and response to audit log table.

Learning focus:
- API + DB integration
- auth persistence
- secure logging

## Phase 3: Document Ingestion Pipeline

Goal:
- Admin can upload documents and create searchable chunks.

Tasks:
1. Add upload endpoint (admin only).
2. Parse PDF, DOCX, TXT.
3. Chunk text with overlap.
4. Generate embeddings.
5. Store in vector DB with metadata.

Learning focus:
- ingestion architecture
- chunk quality
- metadata design

## Phase 4: Real RAG Retrieval

Goal:
- Answer from authorized document chunks.

Tasks:
1. Add hybrid retrieval (semantic + keyword).
2. Add metadata pre-filter by department and role.
3. Add reranking.
4. Return citations with document + section/page.
5. Add low-confidence fallback.

Learning focus:
- retrieval quality
- grounded generation
- trust and explainability

## Phase 5: Security Hardening

Goal:
- Add enterprise safety controls.

Tasks:
1. Prompt injection checks on user input.
2. Document content sanitization.
3. PII masking/redaction policy.
4. Access checks at chunk level.
5. Structured audit events.

Learning focus:
- GenAI security
- governance
- safe enterprise AI

## Phase 6: Employee UX and Admin Dashboard

Goal:
- Make product practical for employees and admins.

Tasks:
1. Add simple frontend chat.
2. Add suggested questions by module.
3. Add feedback buttons.
4. Add admin dashboard metrics.
5. Add document version and re-index flow.

Learning focus:
- product thinking
- operations readiness

## Phase 7: Optional n8n Workflows

Goal:
- Add no-code automation where useful.

Tasks:
1. Document approval workflow.
2. Ticket creation workflow when unresolved.
3. Notification workflow for policy updates.

Learning focus:
- hybrid architecture (code + orchestration)

## Daily Build Routine

1. Pick one feature from current phase.
2. Implement smallest working version.
3. Test with 3 realistic queries.
4. Log what failed and why.
5. Improve prompt/retrieval/security.
