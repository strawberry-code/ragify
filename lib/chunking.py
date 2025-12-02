#!/usr/bin/env python3
"""
Semantic chunking utilities using Chonkie and semchunk.
Implements two-level chunking strategy for optimal RAG performance.
"""

import logging
from typing import Optional, TypedDict, List
import tiktoken

logger = logging.getLogger(__name__)

# Custom exception for chunking failures
class ChunkingError(RuntimeError):
    """Raised when semantic chunking cannot be performed."""
    pass


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """
    Count tokens in text using tiktoken.
    
    Args:
        text: Text to count tokens for
        encoding_name: Tiktoken encoding name
        
    Returns:
        Number of tokens
    """
    try:
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception as e:
        logger.warning(f"Token counting failed: {e}, using word‑based fallback")
        # Fallback: approximate 1 token ≈ 1 word
        return len(text.split())


class ChunkTD(TypedDict):
    text: str
    embedding: List[float]
    semantic_block_index: int
    chunk_index: int
    token_count: int
    chunking_method: str
    embedding_model: str

class QdrantPointTD(TypedDict):
    id: str
    vector: List[float]
    payload: dict

def semantic_chunk_text(
    clean_text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50
) -> list[str]:
    """
    First-level semantic chunking using Chonkie.
    
    Creates macro-level semantic blocks that respect document structure
    and semantic boundaries.
    
    Args:
        clean_text: Pre-cleaned text
        chunk_size: Target chunk size in tokens
        chunk_overlap: Overlap between chunks in tokens
        
    Returns:
        List of macro-semantic chunks
    """
    if not clean_text or len(clean_text.strip()) == 0:
        return []
    
    try:
        from chonkie import TokenChunker
        
        # Use tiktoken encoding for token-based chunking
        enc = tiktoken.get_encoding("cl100k_base")
        
        chunker = TokenChunker(
            tokenizer=enc,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        
        chunks = chunker.chunk(clean_text)
        
        # Extract text from chunk objects
        result = [chunk.text for chunk in chunks if hasattr(chunk, 'text')]
        
        logger.info(f"Chonkie created {len(result)} macro-chunks")
        return result
        
    except ImportError as e:
        logger.error("Chonkie not installed, cannot perform semantic chunking")
        raise ChunkingError("Chonkie not installed")
    except Exception as e:
        logger.warning(f"Chonkie failed: {e}, cannot perform semantic chunking")
        raise ChunkingError(str(e))


def fine_chunk_text(
    semantic_blocks: list[str],
    target_tokens: int = 500,
    overlap_tokens: int = 50
) -> list[dict]:
    """
    Second-level fine-grained chunking using semchunk.
    
    Splits macro-semantic blocks into smaller, embedding-ready chunks
    while respecting semantic boundaries.
    
    Args:
        semantic_blocks: List of macro-chunks from Chonkie
        target_tokens: Target size for final chunks (tokens)
        overlap_tokens: Overlap between chunks (tokens)
        
    Returns:
        List of chunk dictionaries with metadata
    """
    if not semantic_blocks:
        return []
    
    final_chunks = []
    
    try:
        from semchunk import chunkerify
        
        # Create chunker once with tiktoken encoding
        chunker = chunkerify("cl100k_base", chunk_size=target_tokens)
        
        for block_idx, block in enumerate(semantic_blocks):
            if not block or len(block.strip()) == 0:
                continue
            
            try:
                # Use semchunk for fine-grained splitting
                # overlap parameter is passed to the chunker call, not constructor
                chunks = chunker(block, overlap=overlap_tokens)
                
                for chunk_idx, chunk_text in enumerate(chunks):
                    token_count = count_tokens(chunk_text)
                    
                    final_chunks.append({
                        'text': chunk_text,
                        'semantic_block_index': block_idx,
                        'chunk_index': chunk_idx,
                        'token_count': token_count,
                        'chunking_method': 'semantic'
                    })
                    
            except Exception as e:
                logger.warning(f"Semchunk failed for block {block_idx}: {e}, using fallback")
                # Fallback: treat whole block as single chunk
                final_chunks.append({
                    'text': block,
                    'semantic_block_index': block_idx,
                    'chunk_index': 0,
                    'token_count': count_tokens(block),
                    'chunking_method': 'fallback'
                })
        
        logger.info(f"Created {len(final_chunks)} final chunks from {len(semantic_blocks)} semantic blocks")
        return final_chunks
        
    except ImportError as e:
        logger.error("Semchunk not installed, cannot perform fine chunking")
        raise ChunkingError("Semchunk not installed")
    except Exception as e:
        logger.warning(f"Semchunk failed: {e}, cannot perform fine chunking")
        raise ChunkingError(str(e))


def _fallback_chunk(
    blocks: list[str],
    target_tokens: int,
    overlap_tokens: int
) -> list[dict]:
    """
    Fallback chunking when semchunk is not available.
    Simple sliding window on character level.
    """
    final_chunks = []
    
    for block_idx, block in enumerate(blocks):
        # Approximate: 1 token ≈ 4 chars
        target_chars = target_tokens * 4
        overlap_chars = overlap_tokens * 4
        
        start = 0
        chunk_idx = 0
        
        while start < len(block):
            end = min(start + target_chars, len(block))
            chunk_text = block[start:end]
            
            if chunk_text.strip():
                final_chunks.append({
                    'text': chunk_text,
                    'semantic_block_index': block_idx,
                    'chunk_index': chunk_idx,
                    'token_count': count_tokens(chunk_text),
                    'chunking_method': 'fallback_simple'
                })
                chunk_idx += 1
            
            start = end - overlap_chars
            if start >= len(block) - overlap_chars:
                break
    
    return final_chunks


def validate_chunk_size(chunk_text: str, max_tokens: int = 2048) -> bool:
    """
    Validate that chunk doesn't exceed embedding model's token limit.

    Args:
        chunk_text: Chunk text to validate
        max_tokens: Maximum allowed tokens (nomic-embed-text: 2048)
        
    Returns:
        True if chunk is within limits
    """
    token_count = count_tokens(chunk_text)
    return token_count <= max_tokens


def create_chunks(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    min_tokens: int = 0,
    max_tokens: int = 2048
) -> list[dict]:
    """
    Create chunks from text using two-level semantic chunking (chonkie + semchunk).

    Pipeline:
    1. Chonkie TokenChunker: creates macro-semantic blocks (2x target size)
    2. Semchunk: refines into fine-grained embedding-ready chunks
    3. Filter: removes too short/long chunks

    Args:
        text: Text to chunk
        chunk_size: Target chunk size in tokens (default: 500)
        chunk_overlap: Overlap between chunks in tokens (default: 50)
        min_tokens: Minimum chunk size to keep (default: 50)
        max_tokens: Maximum chunk size before re-chunking (default: 2048)

    Returns:
        List of chunk dictionaries with text and metadata
    """
    if not text or len(text.strip()) == 0:
        return []

    try:
        # Level 1: Chonkie semantic chunking (macro blocks)
        macro_chunks = semantic_chunk_text(
            text,
            chunk_size=chunk_size * 2,  # Larger blocks first
            chunk_overlap=chunk_overlap
        )

        if not macro_chunks:
            logger.warning("No macro chunks created, using fallback")
            return _fallback_chunk([text], chunk_size, chunk_overlap)

        # Level 2: Semchunk fine-grained chunking
        fine_chunks = fine_chunk_text(
            macro_chunks,
            target_tokens=chunk_size,
            overlap_tokens=chunk_overlap
        )

        # Level 3: Filter and validate
        valid_chunks = filter_chunks(
            fine_chunks,
            min_tokens=min_tokens,
            max_tokens=max_tokens
        )

        logger.info(f"Created {len(valid_chunks)} chunks (chonkie+semchunk pipeline)")
        return valid_chunks

    except ChunkingError as e:
        logger.warning(f"Semantic chunking failed: {e}, using fallback")
        return _fallback_chunk([text], chunk_size, chunk_overlap)
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        return _fallback_chunk([text], chunk_size, chunk_overlap)


def filter_chunks(
    chunks: list[dict],
    min_tokens: int = 0,
    max_tokens: int = 8192
) -> list[dict]:
    """
    Filter chunks by token count.

    Args:
        chunks: List of chunk dictionaries
        min_tokens: Minimum token count - 0 = keep all (default)
        max_tokens: Maximum token count (needs re-chunking)
        
    Returns:
        Filtered list of valid chunks
    """
    valid_chunks = []
    
    for chunk in chunks:
        token_count = chunk.get('token_count', count_tokens(chunk['text']))
        
        if token_count < min_tokens:
            logger.debug(f"Discarding too short chunk: {token_count} tokens")
            continue
        
        if token_count > max_tokens:
            logger.warning(f"Chunk too long ({token_count} tokens), re-chunking...")
            # Re-chunk using direct fallback to avoid recursion
            sub_chunks = _fallback_chunk(
                [chunk['text']],
                target_tokens=max_tokens // 2,
                overlap_tokens=50
            )
            # Only add sub-chunks that are within limits
            for sub_chunk in sub_chunks:
                if sub_chunk['token_count'] <= max_tokens:
                    valid_chunks.append(sub_chunk)
                else:
                    logger.error(f"Sub-chunk still too large ({sub_chunk['token_count']} tokens), skipping")
        else:
            valid_chunks.append(chunk)
    
    return valid_chunks
