import pytest
from app.ingestion.loader import DocumentLoader
from app.ingestion.chunker import SmartChunker
from app.db.bm25_index import BM25Index
from app.db.vector_db import VectorDB
from app.rag.retriever import HybridRetriever
from app.rag.reranker import CrossEncoderReranker
from app.core.config import settings

@pytest.fixture
def sample_chunks():
    docs = DocumentLoader.load_directory(settings.DATA_RAW_DIR)
    chunks = []
    for doc in docs:
        c = SmartChunker.chunk_markdown(doc["doc_id"], doc["title"], doc["content"])
        chunks.extend(c)
    return chunks

def test_bm25_retrieval_exact_hex(sample_chunks):
    bm25 = BM25Index()
    bm25.build(sample_chunks)
    
    results = bm25.search("0x80070005 access denied", top_k=3)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert "0x80070005" in top_chunk.content or "0x80070005" in top_chunk.section
    assert score > 0

def test_vector_db_semantic_search(sample_chunks):
    vdb = VectorDB(embedding_dim=64)
    vdb.build(sample_chunks)
    
    results = vdb.search("out of memory killed container limits", top_k=3)
    assert len(results) > 0
    top_chunk, score = results[0]
    # Should semantically match OOMKilled or Kubernetes guide
    assert "oom" in top_chunk.content.lower() or "memory" in top_chunk.content.lower()

def test_hybrid_rrf_and_reranker(sample_chunks):
    bm25 = BM25Index()
    bm25.build(sample_chunks)
    vdb = VectorDB(embedding_dim=64)
    vdb.build(sample_chunks)
    chunk_map = {c.chunk_id: c for c in sample_chunks}

    retriever = HybridRetriever(bm25, vdb)
    candidates = retriever.retrieve("0x80070005 access denied installer permission", top_k=5)
    assert len(candidates) > 0

    reranker = CrossEncoderReranker()
    reranked = reranker.rerank("0x80070005 access denied installer permission", candidates, chunk_map, top_k=3)
    assert len(reranked) > 0
    top_selected = chunk_map[reranked[0].chunk_id]
    assert "0x80070005" in top_selected.content or "access denied" in top_selected.content.lower()
