import time
from typing import Dict, List, Optional
from ..models.schema import QueryRequest, QueryResponse, RetrievalDebugInfo, DocumentChunk, LatencyBreakdown
from ..services.query_rewriter import QueryRewriter
from ..services.cache import SemanticCache
from ..services.formatter import LLMFormatter
from ..rag.retriever import HybridRetriever
from ..rag.reranker import CrossEncoderReranker
from ..db.bm25_index import BM25Index
from ..db.vector_db import VectorDB
from ..core.config import settings
from ..core.logger import logger

class RAGPipeline:
    def __init__(self, bm25_index: BM25Index, vector_db: VectorDB, cache: SemanticCache):
        self.bm25_index = bm25_index
        self.vector_db = vector_db
        self.cache = cache
        self.retriever = HybridRetriever(bm25_index, vector_db)
        self.reranker = CrossEncoderReranker()
        self.chunk_map: Dict[str, DocumentChunk] = {c.chunk_id: c for c in bm25_index.chunks}

    def update_indices(self, chunks: List[DocumentChunk]):
        self.bm25_index.build(chunks)
        self.vector_db.build(chunks)
        self.chunk_map = {c.chunk_id: c for c in chunks}
        logger.info(f"RAGPipeline updated with {len(chunks)} chunks.")

    async def run(self, request: QueryRequest) -> QueryResponse:
        start_time = time.time()
        raw_error = request.raw_error.strip()
        
        # 1. Query Understanding & Signal Extraction
        extracted_codes, search_intent = QueryRewriter.extract_error_signals(raw_error)
        logger.info(f"Extracted Codes: {extracted_codes} | Intent: '{search_intent}'")

        # 2. Vector computation for intent (used for both cache and retrieval)
        query_vec = None
        try:
            if self.vector_db.vectorizer:
                query_vec = self.vector_db.embed_texts([search_intent], fit=False)
        except Exception as e:
            logger.warning(f"Embedding intent failed: {e}")

        # 3. Semantic Cache Check (Bypass if force_refresh is True)
        if not request.force_refresh and query_vec is not None:
            cached_resp, sim = self.cache.get(search_intent, query_vec)
            if cached_resp is not None:
                return cached_resp

        t0 = time.time()
        # 4. Hybrid Retrieval (BM25 + Dense Vectors with RRF)
        hybrid_candidates = self.retriever.retrieve(
            query=search_intent,
            top_k=settings.TOP_K_HYBRID,
            rrf_k=settings.RRF_K
        )
        t_hybrid = round((time.time() - t0) * 1000, 2)

        t1 = time.time()
        # 5. Cross-Encoder Reranking
        reranked_scores = self.reranker.rerank(
            query=search_intent,
            candidates=hybrid_candidates,
            chunk_map=self.chunk_map,
            top_k=settings.TOP_K_RERANK
        )
        t_rerank = round((time.time() - t1) * 1000, 2)

        # Get high-precision chunk objects
        selected_chunks = [
            self.chunk_map[s.chunk_id]
            for s in reranked_scores
            if s.chunk_id in self.chunk_map
        ]

        t_intent = round((t0 - start_time) * 1000, 2)
        retrieval_ms = round(t_intent + t_hybrid + t_rerank, 2)

        # Debug metadata for transparency in UI
        debug_info = RetrievalDebugInfo(
            extracted_codes=extracted_codes,
            search_intent=search_intent,
            total_chunks_searched=len(self.chunk_map),
            hybrid_top_k=hybrid_candidates,
            reranked_top_k=reranked_scores,
            cache_hit=False,
            cache_similarity=None,
            latency_ms=retrieval_ms,
            uncached_baseline_ms=1200.0,
            latency_saved_pct=0.0,
            stage_breakdown={
                "intent_ms": t_intent,
                "hybrid_search_ms": t_hybrid,
                "reranker_ms": t_rerank
            }
        )

        # 6. Grounded LLM Reasoning & Structured Output
        t_llm_start = time.time()
        response = await LLMFormatter.generate_diagnosis(
            raw_error=raw_error,
            search_intent=search_intent,
            extracted_codes=extracted_codes,
            reranked_chunks=selected_chunks,
            debug_info=debug_info
        )
        llm_ms = round((time.time() - t_llm_start) * 1000, 2)
        total_latency_ms = round((time.time() - start_time) * 1000, 2)

        # Honest production latency breakdown
        latency_breakdown = LatencyBreakdown(
            retrieval_ms=retrieval_ms,
            rerank_ms=t_rerank,
            llm_ms=llm_ms,
            total_ms=total_latency_ms,
            is_cached=False
        )
        response.debug.latency_ms = total_latency_ms
        response.debug.latency_breakdown = latency_breakdown
        response.debug.stage_breakdown["llm_ms"] = llm_ms

        # 7. Store in Semantic Cache
        if query_vec is not None and len(selected_chunks) > 0:
            self.cache.put(search_intent, query_vec, response, total_latency_ms)

        return response
