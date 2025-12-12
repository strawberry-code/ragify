#!/usr/bin/env python3
"""
Qdrant operations for storing and managing document chunks.
Handles batch uploads and point creation.
"""

import logging
import os
import requests
import time
import uuid
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
COLLECTION_NAME = "documentation"
BATCH_SIZE = int(os.getenv('QDRANT_BATCH_SIZE', '100'))  # Increased from 10 for better throughput
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')


def create_point(
    chunk: dict,
    url: str,
    title: str,
    chunk_index: int,
    total_chunks: int,
    file_hash: Optional[str] = None
) -> dict:
    """
    Create a Qdrant point from a chunk.

    Args:
        chunk: Chunk dictionary with 'text', 'embedding', etc.
        url: Source URL or file path
        title: Document title
        chunk_index: Index of this chunk
        total_chunks: Total number of chunks in document
        file_hash: Optional file hash for deduplication

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
            "file_hash": file_hash,  # Add file hash for deduplication
        }
    }


def upload_points(
    points: list[dict],
    collection_name: Optional[str] = None,
    timeout: int = 60,
    retries: int = 3
) -> bool:
    """
    Upload a batch of points to Qdrant with retry logic.

    Args:
        points: List of Qdrant point dictionaries
        collection_name: Target collection name (defaults to COLLECTION_NAME)
        timeout: Request timeout in seconds
        retries: Maximum retry attempts

    Returns:
        True if successful, False otherwise
    """
    if not points:
        return True

    coll = collection_name or COLLECTION_NAME

    headers = {}
    if QDRANT_API_KEY:
        headers['api-key'] = QDRANT_API_KEY

    url = f"{QDRANT_URL}/collections/{coll}/points"

    for attempt in range(retries):
        try:
            response = requests.put(
                url,
                json={"points": points},
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            logger.info(f"Uploaded {len(points)} points to Qdrant")
            return True

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait = int(e.response.headers.get('Retry-After', '5'))
                logger.warning(f"Rate limited, waiting {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                continue
            logger.error(f"HTTP error during upload: {e.response.status_code}")
            return False

        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error (attempt {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False

    logger.error(f"Failed to upload batch after {retries} attempts")
    return False


def batch_upload_chunks(
    chunks: list[dict],
    url: str,
    title: str,
    collection_name: Optional[str] = None,
    batch_size: int = BATCH_SIZE
) -> int:
    """
    Upload chunks to Qdrant in batches.

    Args:
        chunks: List of embedded chunk dictionaries
        url: Source URL
        title: Document title
        collection_name: Target collection name (defaults to COLLECTION_NAME)
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
            if upload_points(points, collection_name=collection_name):
                uploaded_count += len(points)
            points = []

        # Progress logging
        if (i + 1) % 50 == 0:
            logger.info(f"Upload progress: {i + 1}/{total_chunks}")

    # Upload remaining points
    if points:
        if upload_points(points, collection_name=collection_name):
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
        headers = {}
        if QDRANT_API_KEY:
            headers['api-key'] = QDRANT_API_KEY

        # Check Qdrant is reachable (list collections endpoint)
        response = requests.get(
            f"{QDRANT_URL}/collections",
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Qdrant connection failed: {e}")
        return False


def ensure_file_hash_index(collection_name: str) -> bool:
    """
    Crea index su file_hash per query O(1) invece di scroll O(N).

    Chiamare una volta all'inizio del processing per ottimizzare
    i controlli di deduplicazione.

    Args:
        collection_name: Nome della collection

    Returns:
        True se index esiste o creato, False se errore
    """
    headers = {}
    if QDRANT_API_KEY:
        headers['api-key'] = QDRANT_API_KEY

    try:
        # Crea index su file_hash field
        response = requests.put(
            f"{QDRANT_URL}/collections/{collection_name}/index",
            json={
                "field_name": "file_hash",
                "field_schema": "keyword"  # Index ottimale per exact match
            },
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            logger.info(f"Index file_hash creato per {collection_name}")
            return True
        elif response.status_code == 400 and "already exists" in response.text.lower():
            logger.debug(f"Index file_hash già esiste per {collection_name}")
            return True
        else:
            logger.warning(f"Creazione index fallita: {response.status_code} - {response.text[:100]}")
            return False

    except Exception as e:
        logger.debug(f"Index creation skipped: {e}")
        return False


def check_file_hash_exists(file_hash: str, collection_name: str) -> bool:
    """
    Verifica esistenza file_hash usando count() invece di scroll().

    Ottimizzazione: count() è O(1) con index, scroll() è O(N).

    Args:
        file_hash: Hash SHA-256 del file
        collection_name: Nome della collection

    Returns:
        True se hash esiste, False altrimenti
    """
    headers = {"Content-Type": "application/json"}
    if QDRANT_API_KEY:
        headers['api-key'] = QDRANT_API_KEY

    try:
        # Usa count endpoint con filter
        response = requests.post(
            f"{QDRANT_URL}/collections/{collection_name}/points/count",
            json={
                "filter": {
                    "must": [
                        {
                            "key": "file_hash",
                            "match": {"value": file_hash}
                        }
                    ]
                },
                "exact": False  # Approssimato ma veloce (ok per existence check)
            },
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            result = response.json()
            count = result.get("result", {}).get("count", 0)
            return count > 0
        else:
            # Collection non esiste o altro errore
            return False

    except Exception as e:
        logger.debug(f"Hash check failed: {e}")
        return False


class FileHashCache:
    """
    Cache in-memory per file hash durante una sessione di indexing.

    Evita query ripetute a Qdrant per lo stesso hash nella stessa sessione.
    Utile quando si processano file con lo stesso contenuto in directory diverse.
    """

    def __init__(self):
        self._cache: dict[str, bool] = {}
        self._collection: str = ""

    def set_collection(self, collection_name: str):
        """Imposta collection e resetta cache se cambiata."""
        if self._collection != collection_name:
            self._cache.clear()
            self._collection = collection_name
            logger.debug(f"Hash cache reset for collection: {collection_name}")

    def check(self, file_hash: str, collection_name: str) -> bool:
        """
        Check se hash esiste, usando cache locale + query Qdrant.

        Args:
            file_hash: Hash da verificare
            collection_name: Collection target

        Returns:
            True se esiste (in cache o Qdrant), False altrimenti
        """
        self.set_collection(collection_name)

        # Check cache locale prima
        if file_hash in self._cache:
            return self._cache[file_hash]

        # Query Qdrant
        exists = check_file_hash_exists(file_hash, collection_name)

        # Salva in cache
        self._cache[file_hash] = exists
        return exists

    def mark_indexed(self, file_hash: str):
        """Marca hash come indicizzato (appena uploadato)."""
        self._cache[file_hash] = True

    def stats(self) -> dict:
        """Ritorna statistiche cache."""
        return {
            "collection": self._collection,
            "cached_hashes": len(self._cache),
            "indexed_count": sum(1 for v in self._cache.values() if v)
        }
