from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.bootstrap import init_db, seed_demo_users
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        seed_demo_users(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.metrics = {
    "requests_total": 0,
    "requests_success": 0,
    "requests_error": 0,
    "latency_ms_total": 0.0,
}


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = perf_counter()
    app.state.metrics["requests_total"] += 1
    response = await call_next(request)
    elapsed_ms = (perf_counter() - start) * 1000
    app.state.metrics["latency_ms_total"] += elapsed_ms
    if response.status_code < 400:
        app.state.metrics["requests_success"] += 1
    else:
        app.state.metrics["requests_error"] += 1
    return response


@app.get("/")
def root() -> dict:
    return {
        "message": "Private Company Assistant Using RAG API",
        "docs": "/docs",
    }
