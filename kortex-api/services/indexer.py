"""Code indexer: chunking + embeddings via Ollama."""
import ast
import hashlib
import logging
from pathlib import Path
from typing import List, Tuple

import httpx

from config import settings, host_to_container
from services import rag

logger = logging.getLogger(__name__)

SUPPORTED_EXT = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".go": "go",
    ".rs": "rust", ".rb": "ruby", ".java": "java",
    ".cpp": "cpp", ".c": "c", ".php": "php",
    ".html": "html", ".css": "css", ".scss": "scss",
    ".md": "markdown", ".yaml": "yaml", ".yml": "yaml",
    ".json": "json", ".sh": "bash", ".sql": "sql",
}

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "env", "dist", "build", ".next", ".mypy_cache", "migrations",
}

MAX_FILE_SIZE = 300_000  # 300KB


async def get_embedding(text: str) -> List[float]:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"{settings.OLLAMA_URL}/api/embed",
            json={"model": settings.EMBED_MODEL, "input": text},
        )
        return r.json()["embeddings"][0]


def chunk_python(content: str, display_path: str) -> List[Tuple[str, dict]]:
    chunks = []
    try:
        tree = ast.parse(content)
        lines = content.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.col_offset == 0:
                    text = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                    if len(text.strip()) < 30:
                        continue
                    kind = "class" if isinstance(node, ast.ClassDef) else "function"
                    chunks.append((text, {
                        "type": kind, "name": node.name,
                        "start_line": node.lineno, "end_line": node.end_lineno,
                        "file": display_path, "language": "python",
                    }))
    except SyntaxError:
        pass
    return chunks or _line_chunks(content, display_path, "python")


def _line_chunks(content: str, display_path: str, language: str,
                 size: int = 60, overlap: int = 10) -> List[Tuple[str, dict]]:
    lines = content.splitlines()
    chunks = []
    for i in range(0, len(lines), size - overlap):
        block = "\n".join(lines[i: i + size])
        if len(block.strip()) < 20:
            continue
        chunks.append((block, {
            "type": "block", "start_line": i + 1, "end_line": i + len(lines[i: i + size]),
            "file": display_path, "language": language,
        }))
    return chunks


def chunk_file(content: str, display_path: str, language: str) -> List[Tuple[str, dict]]:
    if language == "python":
        return chunk_python(content, display_path)
    return _line_chunks(content, display_path, language)


def _should_skip(rel: Path) -> bool:
    return any(p in SKIP_DIRS or (p.startswith(".") and p not in (".", ".."))
               for p in rel.parts)


async def index_file(host_path: str, project_id: str,
                     display_path: str | None = None) -> int:
    container = host_to_container(host_path)
    path = Path(container)
    if not path.is_file():
        return 0
    if path.stat().st_size > MAX_FILE_SIZE:
        return 0
    lang = SUPPORTED_EXT.get(path.suffix.lower())
    if not lang:
        return 0

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0

    if not content.strip():
        return 0

    label = display_path or host_path
    chunks = chunk_file(content, label, lang)
    if not chunks:
        return 0

    ids, embeddings, docs, metas = [], [], [], []
    for text, meta in chunks:
        cid = hashlib.md5(f"{project_id}:{label}:{meta.get('start_line',0)}".encode()).hexdigest()
        try:
            emb = await get_embedding(text)
            ids.append(cid)
            embeddings.append(emb)
            docs.append(text)
            metas.append(meta)
        except Exception as e:
            logger.error(f"Embed error {label}: {e}")

    if ids:
        rag.upsert_chunks(project_id, ids, embeddings, docs, metas)
    return len(ids)


async def index_codebase(project_path: str, project_id: str) -> dict:
    root = Path(host_to_container(project_path))
    if not root.exists():
        raise ValueError(f"Path not found: {root}")

    total_files = total_chunks = errors = 0
    for fp in root.rglob("*"):
        if not fp.is_file():
            continue
        if _should_skip(fp.relative_to(root)):
            continue
        if fp.suffix.lower() not in SUPPORTED_EXT:
            continue
        label = f"{project_path}/{fp.relative_to(root)}"
        try:
            n = await index_file(str(fp), project_id, label)
            if n:
                total_files += 1
                total_chunks += n
        except Exception as e:
            logger.error(f"Error indexing {fp}: {e}")
            errors += 1

    return {"files_indexed": total_files, "chunks_created": total_chunks, "errors": errors}
