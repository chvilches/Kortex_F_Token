"""Project registry backed by a JSON file."""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config import settings
from models.schemas import Project, ProjectCreate

logger = logging.getLogger(__name__)
REGISTRY = Path(settings.DATA_DIR) / "projects.json"


def _load() -> dict:
    if not REGISTRY.exists():
        return {}
    try:
        return json.loads(REGISTRY.read_text())
    except Exception:
        return {}


def _save(data: dict):
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(data, indent=2, default=str))


def create(data: ProjectCreate) -> Project:
    reg = _load()
    pid = str(uuid.uuid4())[:8]
    project = Project(
        id=pid,
        name=data.name,
        path=data.path,
        description=data.description,
        created_at=datetime.utcnow(),
    )
    reg[pid] = project.model_dump()
    _save(reg)
    return project


def get(project_id: str) -> Optional[Project]:
    reg = _load()
    d = reg.get(project_id)
    return Project(**d) if d else None


def all_projects() -> List[Project]:
    return [Project(**v) for v in _load().values()]


def update(project_id: str, **kwargs) -> Optional[Project]:
    reg = _load()
    if project_id not in reg:
        return None
    reg[project_id].update({k: v for k, v in kwargs.items() if v is not None})
    _save(reg)
    return Project(**reg[project_id])


def delete(project_id: str) -> bool:
    reg = _load()
    if project_id not in reg:
        return False
    del reg[project_id]
    _save(reg)
    return True
