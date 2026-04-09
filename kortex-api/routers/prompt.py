from fastapi import APIRouter, HTTPException
from models.schemas import PromptBuildRequest, PromptResponse
from services.indexer import get_embedding
from services import rag, projects as proj_svc
from services.prompt_builder import build_prompt, estimate_tokens

router = APIRouter(prefix="/prompt", tags=["prompt"])


@router.post("/build", response_model=PromptResponse)
async def build(req: PromptBuildRequest):
    if req.project_id and not proj_svc.get(req.project_id):
        raise HTTPException(404, "Project not found")

    emb = await get_embedding(req.task)
    chunks = rag.search(emb, req.project_id, req.n_context_chunks)

    if not chunks:
        raise HTTPException(422, "No context found. Index a project first.")

    prompt = await build_prompt(req.task, chunks)

    raw_tokens = sum(len(c.get("content", "")) for c in chunks) // 4
    prompt_tokens = estimate_tokens(prompt)
    return PromptResponse(
        prompt=prompt,
        context_chunks=len(chunks),
        project_id=req.project_id,
        tokens_estimate=prompt_tokens,
        tokens_saved_estimate=max(0, raw_tokens - prompt_tokens),
    )
