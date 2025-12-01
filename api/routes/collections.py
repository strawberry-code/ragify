"""Collections API routes."""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models

router = APIRouter()

# Qdrant configuration
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client with optional API key."""
    if QDRANT_API_KEY:
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return QdrantClient(url=QDRANT_URL)


class CollectionCreate(BaseModel):
    """Request body for creating a collection."""
    name: str
    vector_size: int = 768  # Default for nomic-embed-text


class CollectionInfo(BaseModel):
    """Collection information response."""
    name: str
    points_count: int
    vectors_count: int
    status: str


class DocumentInfo(BaseModel):
    """Document information from collection."""
    url: str
    title: Optional[str]
    chunks_count: int


@router.get("")
async def list_collections():
    """
    List all Qdrant collections.

    Returns:
        dict: List of collections with basic info
    """
    try:
        client = get_qdrant_client()
        collections = client.get_collections()

        result = []
        for collection in collections.collections:
            info = client.get_collection(collection.name)
            result.append({
                "name": collection.name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status.value if info.status else "unknown"
            })

        return {"collections": result, "total": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_collection(body: CollectionCreate):
    """
    Create a new empty collection.

    Args:
        body: Collection name and vector configuration

    Returns:
        dict: Created collection info
    """
    try:
        client = get_qdrant_client()

        # Check if collection already exists
        collections = client.get_collections()
        if any(c.name == body.name for c in collections.collections):
            raise HTTPException(status_code=409, detail=f"Collection '{body.name}' already exists")

        # Create collection
        client.create_collection(
            collection_name=body.name,
            vectors_config=models.VectorParams(
                size=body.vector_size,
                distance=models.Distance.COSINE
            )
        )

        return {
            "message": f"Collection '{body.name}' created",
            "name": body.name,
            "vector_size": body.vector_size
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}")
async def get_collection(name: str):
    """
    Get collection details.

    Args:
        name: Collection name

    Returns:
        dict: Collection information
    """
    try:
        client = get_qdrant_client()
        info = client.get_collection(name)

        return {
            "name": name,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "status": info.status.value if info.status else "unknown",
            "config": {
                "vector_size": info.config.params.vectors.size if info.config.params.vectors else None,
                "distance": info.config.params.vectors.distance.value if info.config.params.vectors else None
            }
        }
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}")
async def delete_collection(name: str):
    """
    Delete a collection.

    Args:
        name: Collection name

    Returns:
        dict: Deletion confirmation
    """
    try:
        client = get_qdrant_client()
        client.delete_collection(name)
        return {"message": f"Collection '{name}' deleted", "name": name}
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/documents")
async def list_documents(name: str, limit: int = 100):
    """
    List documents (unique sources) in a collection.

    Args:
        name: Collection name
        limit: Maximum documents to return

    Returns:
        dict: List of documents with chunk counts
    """
    try:
        client = get_qdrant_client()

        # Scroll through all points to get unique sources
        sources = {}
        offset = None

        while True:
            results, offset = client.scroll(
                collection_name=name,
                limit=1000,
                offset=offset,
                with_payload=["url", "title"],
                with_vectors=False
            )

            for point in results:
                url = point.payload.get("url", "unknown")
                title = point.payload.get("title")

                if url not in sources:
                    sources[url] = {"url": url, "title": title, "chunks_count": 0}
                sources[url]["chunks_count"] += 1

            if offset is None:
                break

        documents = list(sources.values())
        documents.sort(key=lambda x: x["url"])

        return {
            "collection": name,
            "documents": documents[:limit],
            "total": len(documents)
        }
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/stats")
async def collection_stats(name: str):
    """
    Get detailed statistics for a collection.

    Args:
        name: Collection name

    Returns:
        dict: Collection statistics
    """
    try:
        client = get_qdrant_client()
        info = client.get_collection(name)

        # Count unique sources
        sources = set()
        offset = None

        while True:
            results, offset = client.scroll(
                collection_name=name,
                limit=1000,
                offset=offset,
                with_payload=["url"],
                with_vectors=False
            )

            for point in results:
                sources.add(point.payload.get("url", "unknown"))

            if offset is None:
                break

        return {
            "collection": name,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "documents_count": len(sources),
            "status": info.status.value if info.status else "unknown"
        }
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Collection '{name}' not found")
        raise HTTPException(status_code=500, detail=str(e))
