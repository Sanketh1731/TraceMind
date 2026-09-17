from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .core.config import settings
from .core.logger import logger
from .ingestion.loader import DocumentLoader
from .ingestion.chunker import SmartChunker
from .db.bm25_index import BM25Index
from .db.vector_db import VectorDB
from .services.cache import SemanticCache
from .rag.pipeline import RAGPipeline

from .api.query import router as query_router
from .api.upload import router as upload_router
from .api.health import router as health_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load and index documentation
    logger.info("Initializing TraceMind Diagnostic Engine...")
    
    settings.DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    settings.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load raw runbooks
    raw_docs = DocumentLoader.load_directory(settings.DATA_RAW_DIR)
    logger.info(f"Loaded {len(raw_docs)} documents from {settings.DATA_RAW_DIR}")

    # 2. Smart chunking
    all_chunks = []
    for doc in raw_docs:
        chunks = SmartChunker.chunk_markdown(
            doc_id=doc["doc_id"],
            doc_title=doc["title"],
            text=doc["content"]
        )
        all_chunks.extend(chunks)

    logger.info(f"Generated {len(all_chunks)} semantic chunks.")

    # 3. Build Sparse BM25 and Dense Vector indices
    bm25_idx = BM25Index()
    bm25_idx.build(all_chunks)

    vec_db = VectorDB(embedding_dim=settings.EMBEDDING_DIM)
    vec_db.build(all_chunks)

    # 4. Initialize Semantic Cache
    cache = SemanticCache()

    # 5. Initialize RAG Pipeline
    pipeline = RAGPipeline(bm25_idx, vec_db, cache)
    app.state.pipeline = pipeline
    logger.info("TraceMind Pipeline is fully initialized and ready.")

    yield

    # Shutdown: persist cache
    logger.info("Saving state on shutdown...")
    if hasattr(app.state, "pipeline") and app.state.pipeline.cache:
        app.state.pipeline.cache.save()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="TraceMind - AI Debugging Assistant with Grounded Knowledge Retrieval",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(query_router, prefix=settings.API_PREFIX)
app.include_router(upload_router, prefix=settings.API_PREFIX)
app.include_router(health_router, prefix=settings.API_PREFIX)

# Static UI serving for frontend
frontend_dist = settings.BASE_DIR / "frontend" / "dist"
frontend_public = settings.BASE_DIR / "frontend" / "public"

if frontend_dist.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dist)), name="static")

@app.get("/")
def serve_ui():
    index_file = frontend_public / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "TraceMind Backend Active. Visit /api/health for system status, or /docs for API documentation."
    }
