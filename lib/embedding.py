#!/usr/bin/env python3
"""
Embedding generation utilities using Ollama.
Provides safe embedding with token validation.
"""

import logging
import os
import requests
import time
from typing import Optional
from .chunking import count_tokens, validate_chunk_size

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'nomic-embed-text')
MAX_TOKENS = 2048  # nomic-embed-text context limit (configurable models may differ)
EMBEDDING_BATCH_SIZE = int(os.getenv('EMBEDDING_BATCH_SIZE', '3'))  # Low default: batch_size * avg_chunk_tokens must be < 2048


def get_embedding(text: str, timeout: int = 60, max_retries: int = 3) -> Optional[list[float]]:
    """
    Generate embedding using Ollama with retry logic.

    Args:
        text: Text to embed
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts on failure

    Returns:
        Embedding vector or None if failed
    """
    if not text or len(text.strip()) == 0:
        logger.warning("Empty text provided for embedding")
        return None

    token_count = count_tokens(text)
    if token_count > MAX_TOKENS:
        logger.error(f"Text too long for embedding: {token_count} > {MAX_TOKENS} tokens")
        return None

    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "prompt": text,
                    "options": {"num_ctx": MAX_TOKENS}
                },
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()

            if "embedding" not in result:
                logger.error(f"No embedding in response: {result}")
                return None

            return result["embedding"]

        except requests.exceptions.Timeout:
            logger.warning(f"Embedding timeout (attempt {attempt+1}/{max_retries}), retrying...")
            time.sleep(2 ** attempt)
            continue

        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error (attempt {attempt+1}/{max_retries}), retrying...")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            continue

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait = int(e.response.headers.get('Retry-After', '5'))
                logger.warning(f"Rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            elif e.response.status_code == 500:
                logger.warning(f"Ollama 500 error (attempt {attempt+1}/{max_retries}), retrying...")
                time.sleep(2 ** attempt)
                continue
            else:
                logger.error(f"HTTP error from Ollama: {e.response.status_code} - {e.response.text[:200]}")
                return None

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    logger.error(f"Failed to generate embedding after {max_retries} attempts")
    return None


def get_embeddings_batch(
    texts: list[str],
    timeout: int = 120,
    max_retries: int = 3
) -> Optional[list[list[float]]]:
    """
    Generate embeddings for multiple texts in a single API call using Ollama's /api/embed endpoint.

    Args:
        texts: List of texts to embed
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts on failure

    Returns:
        List of embedding vectors (same order as input) or None if failed
    """
    if not texts:
        return []

    # Filter empty texts
    valid_texts = [t for t in texts if t and len(t.strip()) > 0]
    if not valid_texts:
        logger.warning("All texts empty for batch embedding")
        return None

    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/embed",
                json={
                    "model": EMBEDDING_MODEL,
                    "input": valid_texts,
                    "options": {"num_ctx": MAX_TOKENS}
                },
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()

            if "embeddings" not in result:
                logger.error(f"No embeddings in batch response: {result}")
                return None

            return result["embeddings"]

        except requests.exceptions.Timeout:
            logger.warning(f"Batch embedding timeout (attempt {attempt+1}/{max_retries}), retrying...")
            time.sleep(2 ** attempt)
            continue

        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error (attempt {attempt+1}/{max_retries}), retrying...")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            continue

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait = int(e.response.headers.get('Retry-After', '5'))
                logger.warning(f"Rate limited, waiting {wait}s (attempt {attempt+1}/{max_retries})")
                time.sleep(wait)
                continue
            elif e.response.status_code == 500:
                logger.warning(f"Ollama 500 error (attempt {attempt+1}/{max_retries}), retrying...")
                time.sleep(2 ** attempt)
                continue
            else:
                logger.error(f"HTTP error from Ollama: {e.response.status_code} - {e.response.text[:200]}")
                return None

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            return None

    logger.error(f"Failed to generate batch embeddings after {max_retries} attempts")
    return None


def safe_embed_chunk(
    chunk: dict,
    max_tokens: int = MAX_TOKENS,
    re_chunk_on_overflow: bool = True
) -> Optional[dict] | list[dict]:
    """
    Safely embed a chunk with token validation.
    
    If chunk exceeds token limit, can automatically re-chunk.
    
    Args:
        chunk: Chunk dictionary with 'text' key
        max_tokens: Maximum tokens allowed
        re_chunk_on_overflow: If True, re-chunk oversized chunks
        
    Returns:
        - Single chunk dict with 'embedding' if successful
        - List of re-chunked dicts if re-chunking was needed
        - None if failed and re-chunking disabled
    """
    text = chunk.get('text', '')
    
    if not text:
        logger.warning("Empty chunk text, skipping")
        return None
    
    # Validate token count
    if not validate_chunk_size(text, max_tokens):
        token_count = count_tokens(text)
        logger.warning(f"Chunk exceeds token limit: {token_count} > {max_tokens}")
        
        if not re_chunk_on_overflow:
            return None
        
        # Re-chunk this specific chunk
        logger.info(f"Re-chunking oversized chunk ({token_count} tokens)")
        from .chunking import fine_chunk_text
        
        sub_chunks = fine_chunk_text(
            [text],
            target_tokens=max_tokens // 2,
            overlap_tokens=50
        )
        
        # Recursively embed sub-chunks
        result = []
        for sub_chunk in sub_chunks:
            embedded = safe_embed_chunk(sub_chunk, max_tokens, re_chunk_on_overflow=False)
            if embedded:
                result.append(embedded)
        
        return result if result else None
    
    # Generate embedding
    embedding = get_embedding(text)
    
    if embedding is None:
        return None
    
    # Add embedding to chunk
    chunk['embedding'] = embedding
    chunk['embedding_model'] = EMBEDDING_MODEL
    
    return chunk


def batch_embed_chunks(
    chunks: list[dict],
    max_tokens: int = MAX_TOKENS,
    batch_size: int = EMBEDDING_BATCH_SIZE
) -> list[dict]:
    """
    Embed multiple chunks using batch API for better performance.

    Uses Ollama's /api/embed endpoint to embed multiple texts in a single request,
    reducing API calls from N to N/batch_size.

    Args:
        chunks: List of chunk dictionaries with 'text' key
        max_tokens: Maximum tokens per chunk
        batch_size: Number of texts to embed per API call (default: EMBEDDING_BATCH_SIZE env or 10)

    Returns:
        List of successfully embedded chunks (flattened if re-chunking occurred)
    """
    if not chunks:
        return []

    # First pass: validate and prepare chunks, handle oversized ones
    valid_chunks = []
    for chunk in chunks:
        text = chunk.get('text', '')
        if not text or len(text.strip()) == 0:
            continue

        # Use cached token_count if available
        token_count = chunk.get('token_count')
        if token_count is None:
            token_count = count_tokens(text)
            chunk['token_count'] = token_count

        if token_count > max_tokens:
            # Re-chunk oversized chunk
            logger.info(f"Re-chunking oversized chunk ({token_count} tokens)")
            from .chunking import semchunk_text
            sub_chunks = semchunk_text(text, target_tokens=max_tokens // 2, overlap_tokens=50)
            valid_chunks.extend(sub_chunks)
        else:
            valid_chunks.append(chunk)

    if not valid_chunks:
        logger.warning("No valid chunks to embed")
        return []

    # Second pass: batch embed
    embedded_chunks = []
    failed_count = 0

    for i in range(0, len(valid_chunks), batch_size):
        batch = valid_chunks[i:i + batch_size]
        texts = [c.get('text', '') for c in batch]

        logger.info(f"Embedding batch {i // batch_size + 1}/{(len(valid_chunks) + batch_size - 1) // batch_size} ({len(batch)} chunks)")

        embeddings = get_embeddings_batch(texts)

        if embeddings is None:
            # Fallback to single embedding if batch fails
            logger.warning("Batch embedding failed, falling back to single embedding")
            for chunk in batch:
                embedding = get_embedding(chunk.get('text', ''))
                if embedding:
                    chunk['embedding'] = embedding
                    chunk['embedding_model'] = EMBEDDING_MODEL
                    embedded_chunks.append(chunk)
                else:
                    failed_count += 1
        else:
            for chunk, embedding in zip(batch, embeddings):
                chunk['embedding'] = embedding
                chunk['embedding_model'] = EMBEDDING_MODEL
                embedded_chunks.append(chunk)

    if failed_count > 0:
        logger.warning(f"Failed to embed {failed_count}/{len(valid_chunks)} chunks")

    logger.info(f"Successfully embedded {len(embedded_chunks)} chunks")
    return embedded_chunks
