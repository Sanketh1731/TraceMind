from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class QueryRequest(BaseModel):
    raw_error: str = Field(..., description="Raw log, error message, or stack trace pasted by user")
    force_refresh: bool = Field(False, description="Bypass semantic cache if true")
    selected_doc_id: Optional[str] = Field(None, description="Optional doc filter")

class FixStep(BaseModel):
    step_number: int
    title: str
    instruction: str
    code_snippet: Optional[str] = None
    rationale: Optional[str] = None
    priority: Optional[str] = None # e.g. "Priority 1 (Try First - 85% of cases)"
    likelihood: Optional[str] = None # e.g. "Most Common", "Common", "Advanced", "Edge Case"

class Citation(BaseModel):
    doc_id: str
    title: str
    page_or_section: str
    snippet: str
    relevance_explanation: Optional[str] = None
    match_score: Optional[float] = None

class ChunkScore(BaseModel):
    chunk_id: str
    doc_id: str
    section: str
    bm25_score: float
    vector_score: float
    rrf_score: float
    rerank_score: Optional[float] = None
    promotion_reason: Optional[str] = None
    snippet_preview: str

class ConfidenceFactor(BaseModel):
    name: str
    weight_pct: int
    score_pct: int
    contribution_pct: int
    description: str

class ConfidenceAudit(BaseModel):
    overall_pct: int
    level: str
    formula: str = "35% Error Code + 35% Reranker + 15% Vector + 15% BM25 - Ambiguity Discount"
    factors: List[ConfidenceFactor] = []
    supporting_signals: List[str] = [] # [+] Verbatim token match, [+] Section heading alignment
    risk_signals: List[str] = []       # [-] Multiple competing root causes, etc.

class LatencyBreakdown(BaseModel):
    retrieval_ms: float = 0.0
    rerank_ms: float = 0.0
    llm_ms: float = 0.0
    total_ms: float = 0.0
    is_cached: bool = False

class RetrievalDebugInfo(BaseModel):
    extracted_codes: List[str] = []
    search_intent: str
    total_chunks_searched: int
    hybrid_top_k: List[ChunkScore] = []
    reranked_top_k: List[ChunkScore] = []
    cache_hit: bool = False
    cache_similarity: Optional[float] = None
    latency_ms: float = 0.0
    uncached_baseline_ms: float = 1200.0
    latency_saved_pct: Optional[float] = None
    stage_breakdown: Dict[str, float] = {}
    latency_breakdown: Optional[LatencyBreakdown] = None

class CauseRanking(BaseModel):
    most_likely: List[str] = []
    possible: List[str] = []

class QueryResponse(BaseModel):
    query_intent: str
    quick_fix: Optional[str] = None # ⚡ Instant 1-line actionable fix for fast operator scanning
    impact: Optional[str] = None # 💥 1-line system-level impact explanation
    root_cause: str # Human-first diagnosis headline
    explanation: str # Layered technical breakdown
    cause_ranking: Optional[CauseRanking] = None # Ranked alternative causes (most likely vs possible)
    fix_steps: List[FixStep]
    confidence: str # 'high', 'medium', 'low'
    confidence_score: float = 0.90 # 0.0 to 1.0
    confidence_audit: Optional[ConfidenceAudit] = None
    warning: Optional[str] = None
    suggestions: List[str] = []
    citations: List[Citation]
    debug: RetrievalDebugInfo
    timestamp: str

class DocumentChunk(BaseModel):
    chunk_id: str
    doc_id: str
    doc_title: str
    section: str
    content: str
    token_count: int
    metadata: Dict[str, Any] = {}

class CacheStats(BaseModel):
    total_entries: int
    hit_count: int
    miss_count: int
    hit_rate_pct: float
    avg_cached_latency_ms: float
    avg_uncached_latency_ms: float

class IngestResponse(BaseModel):
    status: str
    documents_processed: int
    chunks_created: int
    bm25_terms_indexed: int
    vector_dimension: int
