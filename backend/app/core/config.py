import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "TraceMind"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_RAW_DIR: Path = BASE_DIR / "data" / "raw"
    DATA_PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    
    # Retrieval configuration
    TOP_K_HYBRID: int = 12
    TOP_K_RERANK: int = 4
    RRF_K: int = 60
    BM25_WEIGHT: float = 0.5
    VECTOR_WEIGHT: float = 0.5
    
    # Semantic Cache configuration
    SEMANTIC_CACHE_THRESHOLD: float = 0.88
    MAX_CACHE_ENTRIES: int = 500
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto") # auto, gemini, openai, anthropic, offline
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
    
    # Embeddings
    EMBEDDING_DIM: int = 384
    
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
