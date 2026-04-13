from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/ready")
def ready() -> dict:
    return {"ready": True}


@router.get("/metrics")
def metrics(request: Request) -> dict:
    data = getattr(request.app.state, "metrics", None)
    if not data:
        return {
            "requests_total": 0,
            "requests_success": 0,
            "requests_error": 0,
            "avg_latency_ms": 0.0,
        }

    total = max(1, data["requests_total"])
    avg_latency = data["latency_ms_total"] / total
    return {
        "requests_total": data["requests_total"],
        "requests_success": data["requests_success"],
        "requests_error": data["requests_error"],
        "avg_latency_ms": round(avg_latency, 2),
    }
