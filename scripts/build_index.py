#!/usr/bin/env python3
"""
TraceMind Index Builder CLI
Rebuilds BM25 and Vector indices from raw documentation.
"""
from ingest_docs import run_ingestion

if __name__ == "__main__":
    run_ingestion()
