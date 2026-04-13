from fastapi import APIRouter

from app.api.v1 import admin, auth, chat, documents, feedback, health, ops, workflows
from app.core.config import settings

api_router = APIRouter(prefix=settings.api_v1_prefix)
api_router.include_router(health.router, tags=["health"])
api_router.include_router(ops.router, prefix="/ops", tags=["ops"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
