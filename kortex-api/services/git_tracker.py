"""Git tracker: indexes commits and diffs into RAG."""
import hashlib
import logging
import subprocess
from typing import List, Dict

import httpx

from config import settings, host_to_container
from services import rag
from services.indexer import get_embedding

logger = logging.getLogger(__name__)


def _git(args: List[str], cwd: str) -> str:
    try:
        r = subprocess.run(
            ["git"] + args, cwd=cwd,
            capture_output=True, text=True, timeout=30
        )
        return r.stdout if r.returncode == 0 else ""
    except Exception as e:
        logger.error(f"git error: {e}")
        return ""


def get_recent_commits(project_path: str, n: int = 20) -> List[Dict]:
    cwd = host_to_container(project_path)
    out = _git(["log", f"-{n}", "--pretty=format:%H|%an|%aI|%s"], cwd)
    commits = []
    for line in out.strip().splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({"hash": parts[0], "author": parts[1],
                            "date": parts[2], "message": parts[3]})
    return commits


def get_current_diff(project_path: str) -> Dict[str, str]:
    cwd = host_to_container(project_path)
    return {
        "staged": _git(["diff", "--cached"], cwd),
        "unstaged": _git(["diff"], cwd),
    }


def get_commit_diff(project_path: str, commit_hash: str) -> str:
    cwd = host_to_container(project_path)
    return _git(["show", "--stat", "--patch", "--no-color", commit_hash], cwd)


async def index_commits(project_path: str, project_id: str) -> dict:
    commits = get_recent_commits(project_path)
    indexed = 0
    for commit in commits:
        diff = get_commit_diff(project_path, commit["hash"])
        if not diff:
            continue
        summary = (
            f"Commit {commit['hash'][:8]}: {commit['message']}\n"
            f"Author: {commit['author']} | Date: {commit['date']}\n"
            f"Changes:\n{diff[:2500]}"
        )
        cid = hashlib.md5(f"commit:{project_id}:{commit['hash']}".encode()).hexdigest()
        try:
            emb = await get_embedding(summary)
            rag.upsert_chunks(project_id, [cid], [emb], [summary], [{
                "type": "git_commit",
                "commit_hash": commit["hash"],
                "author": commit["author"],
                "date": commit["date"],
                "message": commit["message"],
                "file": f"git://commit/{commit['hash'][:8]}",
                "language": "git",
            }])
            indexed += 1
        except Exception as e:
            logger.error(f"Error indexing commit {commit['hash']}: {e}")
    return {"commits_indexed": indexed}


def install_git_hook(project_path: str, api_url: str | None = None) -> bool:
    from pathlib import Path
    if api_url is None:
        api_url = f"http://localhost:{settings.API_HOST_PORT}"
    hooks_dir = Path(host_to_container(project_path)) / ".git" / "hooks"
    if not hooks_dir.exists():
        return False
    hook = hooks_dir / "post-commit"
    hook.write_text(
        f"#!/bin/bash\n"
        f"curl -s -X POST {api_url}/ingest/git-hook \\\n"
        f"  -H 'Content-Type: application/json' \\\n"
        f"  -d '{{\"project_path\": \"{project_path}\"}}' &\n"
    )
    hook.chmod(0o755)
    return True
