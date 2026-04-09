from fastapi import APIRouter, HTTPException
from models.schemas import SearchRequest, SearchResult
from services.indexer import get_embedding
from services import rag

router = APIRouter(prefix="/context", tags=["context"])


@router.post("/search")
async def search(req: SearchRequest):
    emb = await get_embedding(req.query)
    chunks = rag.search(emb, req.project_id, req.n_results)
    results = []
    for c in chunks:
        meta = c.get("metadata", {})
        results.append(SearchResult(
            content=c["content"],
            file_path=meta.get("file", "unknown"),
            project_id=c["project_id"],
            score=round(1 - c["distance"], 4),
            chunk_type=meta.get("type", "block"),
            language=meta.get("language"),
        ))
    return results
