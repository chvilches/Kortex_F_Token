"""ChromaDB RAG engine."""
import logging
from typing import List, Optional
import chromadb
from config import settings

logger = logging.getLogger(__name__)
_client: Optional[chromadb.HttpClient] = None


def get_client() -> chromadb.HttpClient:
    global _client
    if _client is None:
        _client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    return _client


def get_collection(project_id: str):
    return get_client().get_or_create_collection(
        name=f"proj_{project_id}",
        metadata={"hnsw:space": "cosine"}
    )


def upsert_chunks(
    project_id: str,
    ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: List[dict],
):
    get_collection(project_id).upsert(
        ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
    )


def search(
    query_embedding: List[float],
    project_id: Optional[str],
    n_results: int = 8,
) -> List[dict]:
    client = get_client()
    collections = (
        [get_collection(project_id)]
        if project_id
        else [
            client.get_collection(c.name)
            for c in client.list_collections()
            if c.name.startswith("proj_")
        ]
    )

    results = []
    for col in collections:
        try:
            count = col.count()
            if count == 0:
                continue
            r = col.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, count),
                include=["documents", "metadatas", "distances"],
            )
            pid = col.name.replace("proj_", "")
            for doc, meta, dist in zip(
                r["documents"][0], r["metadatas"][0], r["distances"][0]
            ):
                results.append(
                    {"content": doc, "metadata": meta, "distance": dist, "project_id": pid}
                )
        except Exception as e:
            logger.warning(f"Search error in {col.name}: {e}")

    results.sort(key=lambda x: x["distance"])
    return results[:n_results]


def delete_project(project_id: str):
    try:
        get_client().delete_collection(f"proj_{project_id}")
    except Exception as e:
        logger.warning(f"Could not delete collection for {project_id}: {e}")


def count_chunks(project_id: str) -> int:
    try:
        return get_collection(project_id).count()
    except Exception:
        return 0
