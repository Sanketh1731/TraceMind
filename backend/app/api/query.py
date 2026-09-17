from fastapi import APIRouter, HTTPException, Request
from ..models.schema import QueryRequest, QueryResponse
from ..rag.evaluator import GroundingEvaluator
from ..core.logger import logger

router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=QueryResponse)
async def submit_query(query_req: QueryRequest, request: Request):
    pipeline = getattr(request.app.state, "pipeline", None)
    if not pipeline:
        raise HTTPException(status_code=503, detail="RAG Pipeline is still initializing.")
    
    try:
        response = await pipeline.run(query_req)
        return response
    except Exception as e:
        logger.error(f"Error executing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Diagnostic error: {str(e)}")

@router.post("/evaluate")
async def evaluate_response(response: QueryResponse, request: Request):
    pipeline = getattr(request.app.state, "pipeline", None)
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not ready.")
    audit = GroundingEvaluator.evaluate(response, pipeline.chunk_map)
    return audit
