"""File system watcher using watchdog."""
import asyncio
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from config import host_to_container
from services.indexer import SUPPORTED_EXT, SKIP_DIRS

logger = logging.getLogger(__name__)


class _Handler(FileSystemEventHandler):
    def __init__(self, project_id: str, loop: asyncio.AbstractEventLoop):
        self.project_id = project_id
        self.loop = loop
        self._pending: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            self._queue(event.src_path)

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            self._queue(event.src_path)

    def _queue(self, path: str):
        p = Path(path)
        if p.suffix.lower() not in SUPPORTED_EXT:
            return
        if any(part in SKIP_DIRS for part in p.parts):
            return
        with self._lock:
            self._pending[path] = time.time()
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(2.0, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self):
        with self._lock:
            files = list(self._pending.keys())
            self._pending.clear()
        from services.indexer import index_file
        for fp in files:
            logger.info(f"[watcher] auto-indexing: {fp}")
            fut = asyncio.run_coroutine_threadsafe(
                index_file(fp, self.project_id), self.loop
            )
            try:
                n = fut.result(timeout=60)
                logger.info(f"[watcher] indexed {n} chunks from {fp}")
            except Exception as e:
                logger.error(f"[watcher] error: {e}")


class WatcherManager:
    def __init__(self):
        self._observers: Dict[str, Observer] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def start(self, project_id: str, project_path: str) -> bool:
        if project_id in self._observers:
            return True
        container = host_to_container(project_path)
        if not Path(container).exists():
            logger.error(f"Path not found: {container}")
            return False
        handler = _Handler(project_id, self._loop)
        obs = Observer()
        obs.schedule(handler, container, recursive=True)
        obs.start()
        self._observers[project_id] = obs
        logger.info(f"[watcher] watching {container} (project={project_id})")
        return True

    def stop(self, project_id: str) -> bool:
        obs = self._observers.pop(project_id, None)
        if obs:
            obs.stop()
            obs.join()
            return True
        return False

    def list(self) -> list:
        return list(self._observers.keys())

    def stop_all(self):
        for pid in list(self._observers):
            self.stop(pid)


watcher_manager = WatcherManager()
