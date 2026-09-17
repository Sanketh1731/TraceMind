from typing import List, Dict
from ..db.bm25_index import BM25Index
from ..db.vector_db import VectorDB
from ..models.schema import DocumentChunk, ChunkScore
from ..core.config import settings
from ..core.logger import logger

class HybridRetriever:
    def __init__(self, bm25_index: BM25Index, vector_db: VectorDB):
        self.bm25 = bm25_index
        self.vector_db = vector_db

    def retrieve(self, query: str, top_k: int = 10, rrf_k: int = 60) -> List[ChunkScore]:
        """
        Executes BM25 and Vector queries in parallel, combining via Reciprocal Rank Fusion (RRF).
        """
        bm25_results = self.bm25.search(query, top_k=top_k * 2)
        vector_results = self.vector_db.search(query, top_k=top_k * 2)

        # Build chunk map
        chunk_map: Dict[str, DocumentChunk] = {}
        bm25_ranks: Dict[str, int] = {}
        bm25_raw_scores: Dict[str, float] = {}

        for rank, (chunk, score) in enumerate(bm25_results):
            chunk_map[chunk.chunk_id] = chunk
            bm25_ranks[chunk.chunk_id] = rank + 1
            bm25_raw_scores[chunk.chunk_id] = score

        vector_ranks: Dict[str, int] = {}
        vector_raw_scores: Dict[str, float] = {}

        for rank, (chunk, score) in enumerate(vector_results):
            chunk_map[chunk.chunk_id] = chunk
            vector_ranks[chunk.chunk_id] = rank + 1
            vector_raw_scores[chunk.chunk_id] = score

        # Compute RRF score for all candidate chunks
        all_chunk_ids = set(bm25_ranks.keys()).union(set(vector_ranks.keys()))
        combined_scores: List[ChunkScore] = []

        for cid in all_chunk_ids:
            chunk = chunk_map[cid]
            b_rank = bm25_ranks.get(cid, 9999)
            v_rank = vector_ranks.get(cid, 9999)

            # Reciprocal Rank Fusion formula
            rrf_val = (1.0 / (rrf_k + b_rank)) + (1.0 / (rrf_k + v_rank))

            # Snippet preview
            content_preview = chunk.content.replace("\n", " ")[:160] + "..."

            combined_scores.append(ChunkScore(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                section=chunk.section,
                bm25_score=round(bm25_raw_scores.get(cid, 0.0), 3),
                vector_score=round(vector_raw_scores.get(cid, 0.0), 3),
                rrf_score=round(rrf_val, 4),
                snippet_preview=content_preview
            ))

        # Sort by RRF score descending
        combined_scores.sort(key=lambda x: x.rrf_score, reverse=True)
        return combined_scores[:top_k]
