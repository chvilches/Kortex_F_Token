"""Kortex Supervisor API — FastAPI main entry point."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.projects import router as projects_router, ingest_router, watch_router
from routers.context import router as context_router
from routers.prompt import router as prompt_router
from services.watcher import watcher_manager
from services import projects as proj_svc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pass current event loop to watcher so it can schedule coroutines
    loop = asyncio.get_event_loop()
    watcher_manager.set_loop(loop)

    # Resume watchers for projects marked as watching
    for p in proj_svc.all_projects():
        if p.is_watching:
            ok = watcher_manager.start(p.id, p.path)
            logger.info(f"Resumed watcher for {p.name} ({p.id}): {'ok' if ok else 'failed'}")

    yield

    watcher_manager.stop_all()
    logger.info("Watchers stopped.")


app = FastAPI(
    title="Kortex Supervisor",
    description="RAG-powered Claude Code supervisor using local llama3.2",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(ingest_router)
app.include_router(watch_router)
app.include_router(context_router)
app.include_router(prompt_router)


@app.get("/")
async def root():
    return {
        "service": "Kortex Supervisor",
        "version": "1.0.0",
        "status": "running",
        "watching": watcher_manager.list(),
    }


@app.get("/health")
async def health():
    return {"ok": True}
