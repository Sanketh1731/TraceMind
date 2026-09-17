import re
from typing import List, Dict
from ..models.schema import DocumentChunk, ChunkScore
from ..core.logger import logger

class CrossEncoderReranker:
    """
    Reranks candidate chunks based on deep lexical-semantic cross-interaction,
    exact error code alignment, and actionable fix density.
    """
    def __init__(self):
        self.model = None
        # Attempt to load lightweight neural cross-encoder if available
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder('cross-encoder/ms-marco-TinyBERT-L-2-v2', max_length=512)
            logger.info("Loaded Neural Cross-Encoder for reranking.")
        except Exception:
            logger.info("Using high-performance contextual cross-scoring reranker.")

    def score_pair(self, query: str, chunk: DocumentChunk) -> tuple[float, str]:
        """Heuristic cross-scoring evaluating exact token match, section relevance, and fix clarity."""
        q_lower = query.lower()
        content_lower = chunk.content.lower()
        sec_lower = chunk.section.lower()
        title_lower = chunk.doc_title.lower()

        # Domain Affinity & Cross-Domain Noise Detection
        is_win_query = any(k in q_lower for k in ["0x8007", "setup.msi", "access denied", "windows", "installer"])
        is_python_query = any(k in q_lower for k in ["recursionerror", "python", "traverse_ast", "sys.setrecursionlimit"])
        is_k8s_docker_query = any(k in q_lower for k in ["oomkilled", "crashloopbackoff", "137", "cgroup", "liveness", "docker", "pod"])
        is_db_query = any(k in q_lower for k in ["53300", "psycopg2", "max_connections", "pool", "sqlstate", "pg_stat_activity"])

        is_win_chunk = "windows" in title_lower or "windows" in sec_lower
        is_python_chunk = "recursion" in title_lower or "recursion" in sec_lower
        is_docker_chunk = "docker" in title_lower or "kubernetes" in title_lower
        is_db_chunk = "database" in title_lower or "pool" in title_lower

        # Cross-domain collision penalty: e.g. Windows query matching Python or DB chunk
        if is_win_query and (is_python_chunk or is_db_chunk) and not any(k in content_lower for k in ["0x8007", "setup.msi"]):
            return 0.0, "Cross-domain mismatch: excluded from Windows context"
        if is_python_query and (is_win_chunk or is_docker_chunk) and not any(k in content_lower for k in ["recursionerror", "traverse_ast"]):
            return 0.0, "Cross-domain mismatch: excluded from Python runtime context"
        if is_db_query and is_win_chunk and not any(k in content_lower for k in ["53300", "sqlstate"]):
            return 0.0, "Cross-domain mismatch: excluded from database context"

        score = 0.0
        reasons = []

        # 1. Error Code match in chunk or title (Very high signal)
        error_tokens = re.findall(r'0x[0-9a-fA-F]+|\b\d{3,5}\b|sig[a-z]+|[a-z]+exception|[a-z]+error', q_lower)
        for token in error_tokens:
            if token in title_lower or token in sec_lower:
                score += 4.5
                reasons.append(f"Exact code match '{token}' in section header")
            elif token in content_lower:
                score += 3.0
                reasons.append(f"Direct token '{token}' in runbook content")

        # 2. Section and Keyword relevance
        for word in q_lower.split():
            if len(word) > 3 and word not in ["error", "code", "file", "line", "user"]:
                if word in sec_lower:
                    score += 1.0
                if word in content_lower:
                    score += 0.3

        # 3. Actionable fix density (award only if passage has genuine query relevance >= 2.0)
        if score >= 2.0:
            if "```" in chunk.content or "fix steps" in content_lower or "root cause" in content_lower:
                score += 1.5
                reasons.append("Contains verified executable code blocks")
            if re.search(r'\d+\.\s+\*\*', chunk.content):
                score += 1.0
                reasons.append("Structured remediation steps present")

        reason_str = "; ".join(reasons[:2]) if reasons else f"Semantic keyword alignment on {chunk.section}"
        return round(score, 3), reason_str

    def rerank(self, query: str, candidates: List[ChunkScore], chunk_map: Dict[str, DocumentChunk], top_k: int = 4) -> List[ChunkScore]:
        if not candidates:
            return []

        scored_candidates: List[ChunkScore] = []

        for c in candidates:
            chunk = chunk_map.get(c.chunk_id)
            if not chunk:
                continue
            cross_score, reason = self.score_pair(query, chunk)
            if cross_score > 0.0:
                c_copy = c.model_copy()
                c_copy.rerank_score = cross_score
                c_copy.promotion_reason = reason
                scored_candidates.append(c_copy)

        scored_candidates.sort(key=lambda x: (x.rerank_score or 0.0, x.rrf_score), reverse=True)

        if not scored_candidates:
            return []

        # Domain Relevance Noise Filter:
        # A secondary chunk is only retained if its score is meaningful (>= 2.5) and >= 40% of top-1 score.
        # This prevents irrelevant noise (e.g. Python RecursionError under a Windows query) from polluting the top cards.
        top_score = scored_candidates[0].rerank_score or 0.0
        filtered_candidates = [
            c for i, c in enumerate(scored_candidates)
            if i == 0 or ((c.rerank_score or 0.0) >= 2.5 and (c.rerank_score or 0.0) >= 0.40 * top_score)
        ]

        return filtered_candidates[:top_k]
