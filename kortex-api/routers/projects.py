from fastapi import APIRouter, HTTPException
from datetime import datetime

from models.schemas import ProjectCreate, IngestRequest, WatchRequest, GitHookRequest
from services import projects as proj_svc
from services import indexer, git_tracker
from services.rag import count_chunks
from services.watcher import watcher_manager

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects():
    return proj_svc.all_projects()


@router.post("")
async def create_project(data: ProjectCreate):
    return proj_svc.create(data)


@router.get("/{project_id}")
async def get_project(project_id: str):
    p = proj_svc.get(project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    p.chunks_count = count_chunks(project_id)
    p.is_watching = project_id in watcher_manager.list()
    return p


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    from services.rag import delete_project as del_index
    watcher_manager.stop(project_id)
    del_index(project_id)
    ok = proj_svc.delete(project_id)
    if not ok:
        raise HTTPException(404, "Project not found")
    return {"ok": True}


# ── Ingest ────────────────────────────────────────────────────
ingest_router = APIRouter(prefix="/ingest", tags=["ingest"])


@ingest_router.post("/codebase")
async def ingest_codebase(req: IngestRequest):
    p = proj_svc.get(req.project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    stats = await indexer.index_codebase(p.path, req.project_id)
    proj_svc.update(req.project_id,
                    indexed_files=stats["files_indexed"],
                    last_indexed=datetime.utcnow())
    # Also index git history
    git_stats = await git_tracker.index_commits(p.path, req.project_id)
    return {**stats, **git_stats}


@ingest_router.post("/git-hook")
async def git_hook(req: GitHookRequest):
    """Called automatically by post-commit hook."""
    all_p = proj_svc.all_projects()
    matched = [p for p in all_p if p.path == req.project_path]
    if not matched:
        return {"ok": False, "reason": "project not registered"}
    p = matched[0]
    # Re-index changed files from latest commit
    from services.git_tracker import get_recent_commits, get_commit_diff
    commits = get_recent_commits(p.path, n=1)
    if commits:
        diff_text = get_commit_diff(p.path, commits[0]["hash"])
        # Extract changed files from diff
        changed = [
            line.split(" ")[-1].strip()
            for line in diff_text.splitlines()
            if line.startswith("+++") and "b/" in line
        ]
        indexed = 0
        for rel in changed:
            rel = rel.replace("b/", "", 1)
            host_path = f"{p.path}/{rel}"
            n = await indexer.index_file(host_path, p.id, f"{p.path}/{rel}")
            indexed += n
        git_stats = await git_tracker.index_commits(p.path, p.id)
        return {"ok": True, "chunks_indexed": indexed, **git_stats}
    return {"ok": True, "chunks_indexed": 0}


# ── Watch ─────────────────────────────────────────────────────
watch_router = APIRouter(prefix="/watch", tags=["watch"])


@watch_router.post("/start")
async def start_watch(req: WatchRequest):
    p = proj_svc.get(req.project_id)
    if not p:
        raise HTTPException(404, "Project not found")
    ok = watcher_manager.start(req.project_id, p.path)
    if not ok:
        raise HTTPException(500, "Could not start watcher (check path)")
    # Install git hook
    git_tracker.install_git_hook(p.path)
    proj_svc.update(req.project_id, is_watching=True)
    return {"ok": True, "project_id": req.project_id}


@watch_router.post("/stop")
async def stop_watch(req: WatchRequest):
    watcher_manager.stop(req.project_id)
    proj_svc.update(req.project_id, is_watching=False)
    return {"ok": True}


@watch_router.get("/status")
async def watch_status():
    return {"watching": watcher_manager.list()}
