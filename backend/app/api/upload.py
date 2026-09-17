import shutil
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from ..ingestion.loader import DocumentLoader
from ..ingestion.chunker import SmartChunker
from ..models.schema import IngestResponse
from ..core.config import settings
from ..core.logger import logger

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("")
def list_documents(request: Request):
    """Lists all available indexed runbooks and documents."""
    pipeline = getattr(request.app.state, "pipeline", None)
    docs_info: Dict[str, Dict[str, Any]] = {}
    
    if pipeline:
        for chunk in pipeline.chunk_map.values():
            if chunk.doc_id not in docs_info:
                docs_info[chunk.doc_id] = {
                    "doc_id": chunk.doc_id,
                    "title": chunk.doc_title,
                    "chunk_count": 0,
                    "sections": []
                }
            docs_info[chunk.doc_id]["chunk_count"] += 1
            if chunk.section not in docs_info[chunk.doc_id]["sections"]:
                docs_info[chunk.doc_id]["sections"].append(chunk.section)

    return list(docs_info.values())

@router.get("/{doc_id}")
def get_document_content(doc_id: str):
    """Returns the full raw text of a document for the UI document viewer."""
    target_files = list(settings.DATA_RAW_DIR.glob(f"{doc_id}.*"))
    if not target_files:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    
    doc_data = DocumentLoader.load_file(target_files[0])
    return doc_data

@router.post("/upload", response_model=IngestResponse)
async def upload_document(request: Request, file: UploadFile = File(...)):
    """Uploads a new markdown, text, or PDF runbook and re-indexes the pipeline."""
    pipeline = getattr(request.app.state, "pipeline", None)
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized.")

    settings.DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    destination_path = settings.DATA_RAW_DIR / file.filename
    
    try:
        with open(destination_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"Saved uploaded file to {destination_path}")
        
        # Load and chunk
        doc_data = DocumentLoader.load_file(destination_path)
        new_chunks = SmartChunker.chunk_markdown(
            doc_id=doc_data["doc_id"],
            doc_title=doc_data["title"],
            text=doc_data["content"]
        )

        # Merge with existing chunks
        all_chunks = list(pipeline.chunk_map.values())
        # Remove any existing chunks with same doc_id
        all_chunks = [c for c in all_chunks if c.doc_id != doc_data["doc_id"]]
        all_chunks.extend(new_chunks)

        pipeline.update_indices(all_chunks)

        return IngestResponse(
            status="success",
            documents_processed=1,
            chunks_created=len(new_chunks),
            bm25_terms_indexed=len(pipeline.bm25_index.corpus_tokens),
            vector_dimension=pipeline.vector_db.vectors.shape[1] if pipeline.vector_db.vectors is not None else 0
        )
    except Exception as e:
        logger.error(f"Failed to process uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(e)}")
