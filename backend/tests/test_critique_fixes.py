import pytest
import asyncio
from app.services.formatter import LLMFormatter
from app.models.schema import (
    DocumentChunk,
    RetrievalDebugInfo,
    ChunkScore,
    LatencyBreakdown,
    ConfidenceAudit
)

def test_deduplicated_root_cause_and_explanation():
    """Ensure root_cause headline is never repeated inside explanation."""
    sample_content = """
### Problem Description
`psycopg2.OperationalError: FATAL: sorry, too many clients already (SQLSTATE 53300)`

### Root Cause Analysis
The PostgreSQL server has reached its configured max_connections ceiling. Every concurrent backend process in Postgres consumes ~10MB of RAM and dedicated lock table space. Unpooled microservices or sudden traffic spikes cause rapid connection pool exhaustion.

### Grounded Actionable Fix Steps
1. **Deploy PgBouncer**:
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```
"""
    chunk = DocumentChunk(
        chunk_id="db_chunk_1",
        doc_id="database_runbook",
        doc_title="Database Connection Pool Runbook",
        section="PostgreSQL Error 53300",
        content=sample_content,
        token_count=120
    )
    chunk_score = ChunkScore(
        chunk_id="db_chunk_1",
        doc_id="database_runbook",
        section="PostgreSQL Error 53300",
        bm25_score=14.5,
        vector_score=0.88,
        rrf_score=0.032,
        rerank_score=6.2,
        promotion_reason="Exact code match",
        snippet_preview="PostgreSQL server reached max_connections"
    )
    debug = RetrievalDebugInfo(
        extracted_codes=["53300"],
        search_intent="PostgreSQL Error 53300 sorry too many clients already",
        total_chunks_searched=12,
        hybrid_top_k=[chunk_score],
        reranked_top_k=[chunk_score],
        cache_hit=False,
        latency_ms=25.0
    )

    response = LLMFormatter._synthesize_offline(
        raw_error="FATAL: sorry, too many clients already (SQLSTATE 53300)",
        search_intent="PostgreSQL 53300",
        extracted_codes=["53300"],
        chunks=[chunk],
        debug_info=debug
    )

    assert "PostgreSQL" in response.root_cause and "connection" in response.root_cause
    # Guarantee explanation does NOT start with or contain the root cause headline
    assert not response.explanation.startswith(response.root_cause)
    assert "Every concurrent backend process in Postgres consumes ~10MB of RAM" in response.explanation

def test_confidence_audit_calculation():
    """Verify deterministic confidence formula and factors."""
    chunk_score = ChunkScore(
        chunk_id="c1",
        doc_id="doc1",
        section="Section 1",
        bm25_score=14.0,
        vector_score=0.85,
        rrf_score=0.03,
        rerank_score=6.0,
        snippet_preview="test"
    )
    debug = RetrievalDebugInfo(
        extracted_codes=["0x80070005"],
        search_intent="Windows Access Denied 0x80070005",
        total_chunks_searched=10,
        reranked_top_k=[chunk_score]
    )

    # High confidence case: exact code matches chunk
    audit_high = LLMFormatter.calculate_confidence_audit(
        extracted_codes=["0x80070005"],
        content="Error 0x80070005 Access Denied in setup.msi",
        section="Windows Setup 0x80070005",
        debug_info=debug
    )

    assert audit_high.overall_pct >= 80
    assert audit_high.overall_pct <= 92
    assert audit_high.level == "high"
    assert len(audit_high.factors) in [4, 5]
    assert any(f.name == "Exact Error Code Match" for f in audit_high.factors)

    # Low confidence case: ambiguous error with low rerank and no exact code
    weak_chunk_score = ChunkScore(
        chunk_id="c_weak",
        doc_id="doc_weak",
        section="General Overview",
        bm25_score=2.0,
        vector_score=0.25,
        rrf_score=0.005,
        rerank_score=0.8,
        snippet_preview="unknown"
    )
    debug_weak = RetrievalDebugInfo(
        extracted_codes=[],
        search_intent="application randomly stopped responding without error code",
        total_chunks_searched=10,
        reranked_top_k=[weak_chunk_score]
    )
    audit_low = LLMFormatter.calculate_confidence_audit(
        extracted_codes=[],
        content="General guidelines for system monitoring and alerts",
        section="System Overview",
        debug_info=debug_weak
    )

    assert audit_low.overall_pct < 60
    assert audit_low.level == "low"

def test_low_confidence_failure_handling():
    """Verify that low confidence responses include warning and suggestions."""
    weak_chunk = DocumentChunk(
        chunk_id="weak_1",
        doc_id="weak_doc",
        doc_title="General Guidelines",
        section="Troubleshooting General",
        content="### Root Cause Analysis\nGeneric process termination without telemetry.\n\n### Grounded Actionable Fix Steps\n1. **Check Logs**: Check event logs.",
        token_count=50
    )
    weak_chunk_score = ChunkScore(
        chunk_id="weak_1",
        doc_id="weak_doc",
        section="Troubleshooting General",
        bm25_score=1.5,
        vector_score=0.20,
        rrf_score=0.005,
        rerank_score=0.6,
        snippet_preview="generic"
    )
    debug = RetrievalDebugInfo(
        extracted_codes=[],
        search_intent="random unknown freeze",
        total_chunks_searched=10,
        reranked_top_k=[weak_chunk_score]
    )

    response = LLMFormatter._synthesize_offline(
        raw_error="The application randomly stopped responding without error code.",
        search_intent="random unknown freeze",
        extracted_codes=[],
        chunks=[weak_chunk],
        debug_info=debug
    )

    assert response.confidence == "low"
    assert response.warning is not None
    assert "Low Grounding Confidence" in response.warning
    assert len(response.suggestions) >= 2

def test_latency_breakdown_structure():
    """Verify LatencyBreakdown model fields and values."""
    lb = LatencyBreakdown(
        retrieval_ms=28.4,
        rerank_ms=12.1,
        llm_ms=1150.0,
        total_ms=1178.4,
        is_cached=False
    )
    assert lb.retrieval_ms == 28.4
    assert lb.llm_ms == 1150.0
    assert lb.total_ms > 1000.0
    assert not lb.is_cached

def test_context_weighting_startup_race_condition():
    """Verify that operational context clues ('started before DB container ready') prioritize startup race condition."""
    econn_chunk = DocumentChunk(
        chunk_id="node_econn_1",
        doc_id="node_python_runtime_errors",
        doc_title="Node.js & Python Backend Runtime Errors Runbook",
        section="1. Node.js ECONNREFUSED – Connection Refused",
        content="""### Root Cause Analysis
ECONNREFUSED is a socket-level network error.
Primary operational causes:
1. Startup Race Condition & Container Timing: When an application container starts before the database container is fully ready.
2. Container Localhost Isolation (Wrong Host): In containerized environments, 127.0.0.1 refers to the container's private loopback interface.

### Grounded Actionable Fix Steps
1. **Configure Container Service Name in Connection String**: Use db:5432.
2. **Add Container Readiness Dependency in docker-compose.yml**: Use depends_on condition service_healthy.
3. **Implement Connection Retry Loop & wait-for-db Script**: Use wait-for-it.sh.""",
        token_count=120
    )
    chunk_score = ChunkScore(
        chunk_id="node_econn_1",
        doc_id="node_python_runtime_errors",
        section="1. Node.js ECONNREFUSED – Connection Refused",
        bm25_score=12.5,
        vector_score=0.88,
        rrf_score=0.03,
        rerank_score=5.8,
        snippet_preview="ECONNREFUSED is a socket-level network error."
    )
    debug = RetrievalDebugInfo(
        extracted_codes=["ECONNREFUSED"],
        search_intent="ECONNREFUSED connect 127.0.0.1:5432 App started before DB container was ready",
        total_chunks_searched=14,
        reranked_top_k=[chunk_score]
    )

    raw_error = "Error: connect ECONNREFUSED 127.0.0.1:5432\nContext: App started before DB container was ready in docker-compose."

    response = LLMFormatter._synthesize_offline(
        raw_error=raw_error,
        search_intent="ECONNREFUSED connect 127.0.0.1:5432 App started before DB container was ready",
        extracted_codes=["ECONNREFUSED"],
        chunks=[econn_chunk],
        debug_info=debug
    )

    # 1. Must prioritize the startup race condition
    assert "startup race condition" in response.root_cause.lower()
    assert "race condition" in response.explanation.lower() or "asynchronously" in response.explanation.lower()

    # 2. Fix steps must include wait-for-db / healthcheck
    fix_titles = [f.title.lower() for f in response.fix_steps]
    assert any("healthcheck" in t or "readiness" in t for t in fix_titles)
    assert any("retry" in t or "wait-for" in t for t in fix_titles)

    # 3. Confidence must be realistically calibrated in the 85-92% range (not 98%)
    assert 85 <= response.confidence_audit.overall_pct <= 92
    assert response.confidence == "high"

