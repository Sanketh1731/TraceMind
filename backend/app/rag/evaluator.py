from typing import Dict, Any, List
from ..models.schema import QueryResponse, DocumentChunk

class GroundingEvaluator:
    """
    Evaluates factual grounding, citation accuracy, and hallucination absence
    in generated diagnostic responses.
    """
    @staticmethod
    def evaluate(response: QueryResponse, chunk_map: Dict[str, DocumentChunk]) -> Dict[str, Any]:
        total_citations = len(response.citations)
        verified_citations = 0
        citation_details = []

        for cit in response.citations:
            # Check if snippet exists verbatim in the chunk or document
            is_grounded = False
            matching_chunk = None

            for chunk in chunk_map.values():
                if cit.doc_id in chunk.doc_id or chunk.doc_id in cit.doc_id:
                    import re
                    clean_chunk = re.sub(r'\s+', ' ', chunk.content).lower()
                    clean_snippet = re.sub(r'\s+', ' ', cit.snippet).lower().strip(" .")
                    
                    if clean_snippet in clean_chunk or clean_snippet[:40] in clean_chunk:
                        is_grounded = True
                        matching_chunk = chunk.chunk_id
                        break

            if is_grounded:
                verified_citations += 1

            citation_details.append({
                "snippet": cit.snippet[:60] + "...",
                "doc_id": cit.doc_id,
                "grounded": is_grounded,
                "matching_chunk_id": matching_chunk
            })

        grounding_score = (verified_citations / total_citations) if total_citations > 0 else 1.0
        hallucination_risk = "Low" if grounding_score >= 0.8 else ("Moderate" if grounding_score >= 0.5 else "High")

        return {
            "total_citations": total_citations,
            "verified_citations": verified_citations,
            "grounding_score_pct": round(grounding_score * 100, 1),
            "hallucination_risk": hallucination_risk,
            "citations_audit": citation_details
        }
