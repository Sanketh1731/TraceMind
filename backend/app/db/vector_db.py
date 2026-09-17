import pickle
import numpy as np
from pathlib import Path
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from ..models.schema import DocumentChunk
from ..core.logger import logger

class VectorDB:
    def __init__(self, embedding_dim: int = 128):
        self.embedding_dim = embedding_dim
        self.chunks: List[DocumentChunk] = []
        self.vectors: np.ndarray | None = None
        self.vectorizer: TfidfVectorizer | None = None
        self.svd: TruncatedSVD | None = None

    def embed_texts(self, texts: List[str], fit: bool = False) -> np.ndarray:
        """Converts texts to normalized dense vectors using TF-IDF + Latent Semantic Projection."""
        if fit:
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=4000,
                sublinear_tf=True
            )
            tfidf_mat = self.vectorizer.fit_transform(texts)
            n_components = min(self.embedding_dim, tfidf_mat.shape[1] - 1, tfidf_mat.shape[0] - 1)
            if n_components > 1:
                self.svd = TruncatedSVD(n_components=n_components, random_state=42)
                dense_vecs = self.svd.fit_transform(tfidf_mat)
            else:
                dense_vecs = tfidf_mat.toarray()
        else:
            if not self.vectorizer:
                raise ValueError("Vectorizer not fitted yet.")
            tfidf_mat = self.vectorizer.transform(texts)
            if self.svd:
                dense_vecs = self.svd.transform(tfidf_mat)
            else:
                dense_vecs = tfidf_mat.toarray()

        # L2 normalization for fast cosine similarity via dot product
        norms = np.linalg.norm(dense_vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (dense_vecs / norms).astype(np.float32)

    def build(self, chunks: List[DocumentChunk]):
        self.chunks = chunks
        if not chunks:
            self.vectors = None
            return
        
        texts = [f"{c.doc_title} {c.section}\n{c.content}" for c in chunks]
        self.vectors = self.embed_texts(texts, fit=True)
        logger.info(f"VectorDB built with {len(chunks)} vectors (dim={self.vectors.shape[1]}).")

    def search(self, query: str, top_k: int = 10) -> List[Tuple[DocumentChunk, float]]:
        if self.vectors is None or not self.chunks or not self.vectorizer:
            return []
        
        query_vec = self.embed_texts([query], fit=False) # shape (1, dim)
        # Cosine similarity is dot product because vectors are L2-normalized
        scores = np.dot(self.vectors, query_vec.T).squeeze()
        if np.ndim(scores) == 0:
            scores = np.array([scores])
            
        ranked_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.chunks[i], float(scores[i])) for i in ranked_indices]

    def save(self, filepath: Path):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump({
                "chunks": self.chunks,
                "vectors": self.vectors,
                "vectorizer": self.vectorizer,
                "svd": self.svd
            }, f)

    def load(self, filepath: Path) -> bool:
        if not filepath.exists():
            return False
        try:
            with open(filepath, "rb") as f:
                data = pickle.load(f)
                self.chunks = data["chunks"]
                self.vectors = data["vectors"]
                self.vectorizer = data["vectorizer"]
                self.svd = data["svd"]
            return True
        except Exception as e:
            logger.error(f"Failed to load VectorDB: {e}")
            return False
