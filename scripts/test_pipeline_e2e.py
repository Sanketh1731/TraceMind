"""
End-to-End verification script for TraceMind API and RAG Pipeline
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "backend"))

from fastapi.testclient import TestClient
from app.main import app

def run_e2e_test():
    print("=== TraceMind End-to-End API Verification ===")
    
    with TestClient(app) as client:
        # 1. Health check
        print("\n[1] Testing /api/health...")
        resp = client.get("/api/health")
        print("Status:", resp.status_code)
        print("Response:", resp.json())
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
        assert resp.json()["indexed_chunks"] > 0

        # 2. List documents
        print("\n[2] Testing /api/documents...")
        resp = client.get("/api/documents")
        print("Status:", resp.status_code)
        docs = resp.json()
        print(f"Retrieved {len(docs)} documents:")
        for d in docs:
            print(f"  - {d['doc_id']}: {d['chunk_count']} chunks")
        assert len(docs) >= 4

        # 3. Query Windows Permission Error
        print("\n[3] Testing /api/query with Windows 0x80070005 error...")
        query_payload = {
            "raw_error": "Error: 0x80070005 Access Denied while installing package at C:\\Users\\HP\\AppData\\Local\\Temp\\setup.msi",
            "force_refresh": False
        }
        resp = client.post("/api/query", json=query_payload)
        print("Status:", resp.status_code)
        data = resp.json()
        print("Extracted Intent:", data["query_intent"])
        print("Root Cause:", data["root_cause"])
        print("Confidence:", data["confidence"])
        print("Cache Hit:", data["debug"]["cache_hit"])
        print("Latency (ms):", data["debug"]["latency_ms"])
        print("Fix Steps Count:", len(data["fix_steps"]))
        print("Citations Count:", len(data["citations"]))
        assert resp.status_code == 200
        assert len(data["fix_steps"]) > 0
        assert len(data["citations"]) > 0
        assert "0x80070005" in data["citations"][0]["title"] or "0x80070005" in data["root_cause"] or "access denied" in data["root_cause"].lower()

        # 4. Query again (semantic similarity) to verify Semantic Cache HIT
        print("\n[4] Testing Semantic Cache Hit with rephrased query...")
        similar_payload = {
            "raw_error": "Access Denied 0x80070005 error when running msi package installer",
            "force_refresh": False
        }
        resp_cached = client.post("/api/query", json=similar_payload)
        data_cached = resp_cached.json()
        print("Cache Hit Status:", data_cached["debug"]["cache_hit"])
        print("Similarity Score:", data_cached["debug"]["cache_similarity"])
        print("Cached Latency (ms):", data_cached["debug"]["latency_ms"])
        assert data_cached["debug"]["cache_hit"] is True

        # 5. UI HTML endpoint
        print("\n[5] Testing root UI endpoint GET /...")
        ui_resp = client.get("/")
        print("Status:", ui_resp.status_code)
        assert ui_resp.status_code == 200
        assert "TraceMind" in ui_resp.text

        # 6. Evaluation endpoint
        print("\n[6] Testing Grounding Evaluation /api/query/evaluate...")
        eval_resp = client.post("/api/query/evaluate", json=data)
        eval_data = eval_resp.json()
        print("Grounding Score (%):", eval_data["grounding_score_pct"])
        print("Hallucination Risk:", eval_data["hallucination_risk"])
        assert eval_data["hallucination_risk"] in ["Low", "Moderate"]

    print("\n[SUCCESS] ALL TRACEMIND E2E VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_e2e_test()
