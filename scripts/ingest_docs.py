#!/usr/bin/env python3
"""
TraceMind Document Ingestion CLI
Loads markdown and PDF documentation from data/raw, chunks them, and builds indices.
"""
import sys
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "backend"))

from app.core.config import settings
from app.core.logger import logger
from app.ingestion.loader import DocumentLoader
from app.ingestion.chunker import SmartChunker
from app.db.bm25_index import BM25Index
from app.db.vector_db import VectorDB

def run_ingestion():
    logger.info("=== Starting TraceMind Knowledge Ingestion ===")
    logger.info(f"Scanning directory: {settings.DATA_RAW_DIR}")
    
    docs = DocumentLoader.load_directory(settings.DATA_RAW_DIR)
    logger.info(f"Loaded {len(docs)} documents.")

    total_chunks = []
    for doc in docs:
        chunks = SmartChunker.chunk_markdown(doc["doc_id"], doc["title"], doc["content"])
        logger.info(f"  -> '{doc['title']}' produced {len(chunks)} chunks.")
        total_chunks.extend(chunks)

    logger.info(f"Total chunks created: {len(total_chunks)}")

    # Build and serialize BM25 Index
    bm25 = BM25Index()
    bm25.build(total_chunks)
    bm25_path = settings.DATA_PROCESSED_DIR / "bm25_index.pkl"
    bm25.save(bm25_path)
    logger.info(f"Saved BM25 index to {bm25_path}")

    # Build and serialize Vector DB
    vdb = VectorDB(embedding_dim=settings.EMBEDDING_DIM)
    vdb.build(total_chunks)
    vdb_path = settings.DATA_PROCESSED_DIR / "vector_db.pkl"
    vdb.save(vdb_path)
    logger.info(f"Saved VectorDB to {vdb_path}")

    logger.info("=== TraceMind Knowledge Ingestion Complete ===")

if __name__ == "__main__":
    run_ingestion()
