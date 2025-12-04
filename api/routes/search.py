"""Search API routes."""

import os
import warnings
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient

# Suppress Qdrant client version warnings
warnings.filterwarnings("ignore", message=".*Qdrant client version.*incompatible.*")

router = APIRouter()

# Configuration
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'nomic-embed-text')


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client with optional API key."""
    if QDRANT_API_KEY:
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return QdrantClient(url=QDRANT_URL)


@lru_cache(maxsize=1000)
def _cached_embedding(text: str, model: str) -> tuple[float, ...] | None:
    """Generate embedding with LRU cache (returns tuple for hashability)."""
    import requests

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        embedding = response.json().get("embedding")
        return tuple(embedding) if embedding else None
    except Exception:
        return None


def get_embedding(text: str, model: str = None, timeout: int = 30) -> list[float] | None:
    """Generate embedding using Ollama with caching."""
    if model is None:
        model = EMBEDDING_MODEL

    # Use cached version (returns tuple, convert back to list)
    result = _cached_embedding(text, model)
    return list(result) if result else None


class SearchRequest(BaseModel):
    """Search request body."""
    query: str
    collection: str = "documentation"
    limit: int = 5


class SearchResult(BaseModel):
    """Single search result."""
    score: float
    url: str
    title: Optional[str]
    text: str
    chunk_index: Optional[int]


class SearchResponse(BaseModel):
    """Search response."""
    query: str
    collection: str
    results: list[SearchResult]
    total: int


@router.post("/search")
async def search(request: SearchRequest):
    """
    Semantic search in a collection.

    Args:
        request: Search query, collection, and limit

    Returns:
        dict: Search results with scores
    """
    try:
        # Generate query embedding
        embedding = get_embedding(request.query)
        if not embedding:
            raise HTTPException(
                status_code=503,
                detail="Failed to generate embedding. Is Ollama running?"
            )

        # Search in Qdrant
        client = get_qdrant_client()

        results = client.query_points(
            collection_name=request.collection,
            query=embedding,
            limit=request.limit,
            with_payload=True
        )

        # Format results
        formatted_results = []
        for point in results.points:
            formatted_results.append(SearchResult(
                score=point.score,
                url=point.payload.get("url", ""),
                title=point.payload.get("title"),
                text=point.payload.get("text", "")[:500],  # Truncate
                chunk_index=point.payload.get("chunk_index")
            ))

        return SearchResponse(
            query=request.query,
            collection=request.collection,
            results=formatted_results,
            total=len(formatted_results)
        )

    except HTTPException:
        raise
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{request.collection}' not found"
            )
        raise HTTPException(status_code=500, detail=str(e))
