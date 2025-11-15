#!/usr/bin/env python3
"""
Qdrant operations for storing and managing document chunks.
Handles batch uploads and point creation.
"""

import logging
import requests
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "documentation"
BATCH_SIZE = 10


def create_point(
    chunk: dict,
    url: str,
    title: str,
    chunk_index: int,
    total_chunks: int
) -> dict:
    """
    Create a Qdrant point from a chunk.
    
    Args:
        chunk: Chunk dictionary with 'text', 'embedding', etc.
        url: Source URL
        title: Document title
        chunk_index: Index of this chunk
        total_chunks: Total number of chunks in document
        
    Returns:
        Qdrant point dictionary
    """
    return {
        "id": str(uuid.uuid4()),
        "vector": chunk['embedding'],
        "payload": {
            "_type": "DocumentChunk",
            "text": chunk['text'],
            "url": url,
            "title": title,
            "timestamp": datetime.now().isoformat(),
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "semantic_block_index": chunk.get('semantic_block_index', 0),
            "token_count": chunk.get('token_count', 0),
            "chunking_method": chunk.get('chunking_method', 'unknown'),
            "embedding_model": chunk.get('embedding_model', 'unknown'),
        }
    }


def upload_points(points: list[dict], timeout: int = 60) -> bool:
    """
    Upload a batch of points to Qdrant.
    
    Args:
        points: List of Qdrant point dictionaries
        timeout: Request timeout in seconds
        
    Returns:
        True if successful, False otherwise
    """
    if not points:
        return True
    
    try:
        response = requests.put(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points",
            json={"points": points},
            timeout=timeout
        )
        response.raise_for_status()
        logger.debug(f"Uploaded {len(points)} points to Qdrant")
        return True
    except Exception as e:
        logger.error(f"Failed to upload batch: {e}")
        return False


def batch_upload_chunks(
    chunks: list[dict],
    url: str,
    title: str,
    batch_size: int = BATCH_SIZE
) -> int:
    """
    Upload chunks to Qdrant in batches.
    
    Args:
        chunks: List of embedded chunk dictionaries
        url: Source URL
        title: Document title
        batch_size: Number of points per batch
        
    Returns:
        Number of successfully uploaded chunks
    """
    points = []
    uploaded_count = 0
    total_chunks = len(chunks)
    
    for i, chunk in enumerate(chunks):
        # Create Qdrant point
        point = create_point(chunk, url, title, i, total_chunks)
        points.append(point)
        
        # Upload batch when full
        if len(points) >= batch_size:
            if upload_points(points):
                uploaded_count += len(points)
            points = []
        
        # Progress logging
        if (i + 1) % 50 == 0:
            logger.info(f"Upload progress: {i + 1}/{total_chunks}")
    
    # Upload remaining points
    if points:
        if upload_points(points):
            uploaded_count += len(points)
    
    logger.info(f"Uploaded {uploaded_count}/{total_chunks} chunks for: {title}")
    return uploaded_count


def check_qdrant_connection() -> bool:
    """
    Check if Qdrant is accessible.
    
    Returns:
        True if connected, False otherwise
    """
    try:
        response = requests.get(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}",
            timeout=5
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Qdrant connection failed: {e}")
        return False
