import pytest
import numpy as np
from app.services.cache import SemanticCache
from app.models.schema import QueryResponse, FixStep, Citation, RetrievalDebugInfo

def test_semantic_cache_put_and_hit(tmp_path):
    cache_file = tmp_path / "test_cache.pkl"
    cache = SemanticCache(filepath=cache_file)
    
    # Create fake response
    debug_info = RetrievalDebugInfo(
        extracted_codes=["0x80070005"],
        search_intent="permission denied windows installer",
        total_chunks_searched=10
    )
    resp = QueryResponse(
        query_intent="permission denied windows installer",
        root_cause="Access Denied DACL permissions issue.",
        explanation="The process lacks write access.",
        fix_steps=[FixStep(step_number=1, title="Run as Admin", instruction="Elevate prompt")],
        confidence="high",
        citations=[Citation(doc_id="windows_installation_errors", title="Windows", page_or_section="0x80070005", snippet="Error 0x80070005 indicates that...")],
        debug=debug_info,
        timestamp="2026-09-05T22:45:00"
    )

    # Unit vector
    vec1 = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    cache.put("permission denied windows installer", vec1, resp, latency_ms=1200.0)

    # Test exact / highly similar vector query (sim = 0.999)
    vec_similar = np.array([[0.99, 0.01, 0.0]], dtype=np.float32)
    vec_similar /= np.linalg.norm(vec_similar)

    hit_resp, sim = cache.get("getting permission denied error", vec_similar)
    assert hit_resp is not None
    assert hit_resp.debug.cache_hit is True
    assert sim >= 0.88
    assert cache.hit_count == 1

    # Test dissimilar vector query (sim = 0.0)
    vec_different = np.array([[0.0, 1.0, 0.0]], dtype=np.float32)
    miss_resp, sim_diff = cache.get("kubernetes pod crash", vec_different)
    assert miss_resp is None
    assert cache.miss_count == 1
