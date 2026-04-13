from pydantic import BaseModel


class AdminMetricsResponse(BaseModel):
    total_queries: int
    denied_scope_queries: int
    blocked_injection_queries: int
    low_confidence_fallbacks: int
    top_modules: list[dict[str, int]]
