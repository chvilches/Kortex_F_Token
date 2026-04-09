from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str
    path: str  # absolute host path
    description: Optional[str] = None


class Project(BaseModel):
    id: str
    name: str
    path: str
    description: Optional[str] = None
    created_at: datetime
    indexed_files: int = 0
    chunks_count: int = 0
    last_indexed: Optional[datetime] = None
    is_watching: bool = False


class IngestRequest(BaseModel):
    project_id: str


class WatchRequest(BaseModel):
    project_id: str


class GitHookRequest(BaseModel):
    project_path: str


class SearchRequest(BaseModel):
    query: str
    project_id: Optional[str] = None
    n_results: int = 5


class SearchResult(BaseModel):
    content: str
    file_path: str
    project_id: str
    score: float
    chunk_type: str
    language: Optional[str] = None


class PromptBuildRequest(BaseModel):
    task: str
    project_id: Optional[str] = None
    n_context_chunks: int = 8


class PromptResponse(BaseModel):
    prompt: str
    context_chunks: int
    project_id: Optional[str] = None
    tokens_estimate: int
    tokens_saved_estimate: int
