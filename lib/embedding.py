#!/usr/bin/env python3
"""
Embedding generation utilities using Ollama.
Provides safe embedding with token validation.
"""

import logging
import requests
import time
from typing import Optional
from .chunking import count_tokens, validate_chunk_size

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text"
MAX_TOKENS = 8192  # nomic-embed-text limit


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
                    "prompt": text
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
            time.sleep(2 ** attempt)  # Exponential backoff
            continue
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
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
    max_tokens: int = MAX_TOKENS
) -> list[dict]:
    """
    Embed multiple chunks with progress tracking.
    
    Args:
        chunks: List of chunk dictionaries
        max_tokens: Maximum tokens per chunk
        
    Returns:
        List of successfully embedded chunks (flattened if re-chunking occurred)
    """
    embedded_chunks = []
    failed_count = 0
    
    for i, chunk in enumerate(chunks):
        if i % 10 == 0:
            logger.info(f"Embedding progress: {i}/{len(chunks)}")
        
        result = safe_embed_chunk(chunk, max_tokens)
        
        if result is None:
            failed_count += 1
            continue
        
        # Handle both single chunk and list of re-chunked chunks
        if isinstance(result, list):
            embedded_chunks.extend(result)
        else:
            embedded_chunks.append(result)
    
    if failed_count > 0:
        logger.warning(f"Failed to embed {failed_count}/{len(chunks)} chunks")
    
    logger.info(f"Successfully embedded {len(embedded_chunks)} chunks")
    return embedded_chunks
