import re
import pickle
from pathlib import Path
from typing import List, Tuple
from rank_bm25 import BM25Okapi
from ..models.schema import DocumentChunk
from ..core.logger import logger

# Tokenizer preserving tech tokens (hex, underscores, dots, hyphens in code)
TOKEN_SPLIT_REGEX = re.compile(r'[a-zA-Z0-9_\-\.:#]+')

def tokenize_code_text(text: str) -> List[str]:
    tokens = TOKEN_SPLIT_REGEX.findall(text.lower())
    return [t for t in tokens if len(t) > 1]

class BM25Index:
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.bm25: BM25Okapi | None = None
        self.corpus_tokens: List[List[str]] = []

    def build(self, chunks: List[DocumentChunk]):
        self.chunks = chunks
        self.corpus_tokens = [tokenize_code_text(f"{c.doc_title} {c.section} {c.content}") for c in chunks]
        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)
            logger.info(f"BM25 index built with {len(chunks)} chunks.")
        else:
            self.bm25 = None

    def search(self, query: str, top_k: int = 10) -> List[Tuple[DocumentChunk, float]]:
        if not self.bm25 or not self.chunks:
            return []
        query_tokens = tokenize_code_text(query)
        if not query_tokens:
            return []
        scores = self.bm25.get_scores(query_tokens)
        
        # Zip and rank
        scored_pairs = list(zip(self.chunks, scores))
        scored_pairs.sort(key=lambda x: x[1], reverse=True)
        return scored_pairs[:top_k]

    def save(self, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump({"chunks": self.chunks, "corpus_tokens": self.corpus_tokens}, f)

    def load(self, filepath: Path) -> bool:
        if not filepath.exists():
            return False
        try:
            with open(filepath, "rb") as f:
                data = pickle.load(f)
                self.chunks = data["chunks"]
                self.corpus_tokens = data["corpus_tokens"]
                self.bm25 = BM25Okapi(self.corpus_tokens)
            return True
        except Exception as e:
            logger.error(f"Failed to load BM25 index: {e}")
            return False
