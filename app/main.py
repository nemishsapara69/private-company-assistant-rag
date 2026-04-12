from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings
from app.db.bootstrap import init_db, seed_demo_users
from app.db.session import SessionLocal

app = FastAPI(title=settings.app_name)
app.include_router(api_router)


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_demo_users(db)
    finally:
        db.close()


@app.get("/")
def root() -> dict:
    return {
        "message": "Private Company Assistant Using RAG API",
        "docs": "/docs",
    }
