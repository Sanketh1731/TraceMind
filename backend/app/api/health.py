from fastapi import APIRouter, Request
from ..models.schema import CacheStats
from ..core.config import settings

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def health_check(request: Request):
    pipeline = getattr(request.app.state, "pipeline", None)
    total_chunks = len(pipeline.chunk_map) if pipeline else 0
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "indexed_chunks": total_chunks,
        "semantic_cache_entries": len(pipeline.cache.entries) if pipeline and pipeline.cache else 0
    }

@router.get("/cache", response_model=CacheStats)
def get_cache_stats(request: Request):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline and pipeline.cache:
        return pipeline.cache.get_stats()
    return CacheStats(
        total_entries=0,
        hit_count=0,
        miss_count=0,
        hit_rate_pct=0.0,
        avg_cached_latency_ms=0.0,
        avg_uncached_latency_ms=0.0
    )

@router.post("/cache/clear")
def clear_cache(request: Request):
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline and pipeline.cache:
        pipeline.cache.entries.clear()
        pipeline.cache.hit_count = 0
        pipeline.cache.miss_count = 0
        pipeline.cache.save()
        return {"status": "success", "message": "Semantic cache cleared."}
    return {"status": "error", "message": "Cache not initialized."}
