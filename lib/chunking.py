#!/usr/bin/env python3
"""
Semantic chunking utilities using Chonkie and semchunk.
Implements two-level chunking strategy for optimal RAG performance.
"""

import logging
from typing import Optional
import tiktoken

logger = logging.getLogger(__name__)


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
        logger.warning(f"Token counting failed: {e}, using approximation")
        # Fallback: rough approximation (1 token ≈ 4 characters)
        return len(text) // 4


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
        
    except ImportError:
        logger.error("Chonkie not installed, using fallback")
        return [clean_text]
    except Exception as e:
        logger.warning(f"Chonkie failed: {e}, using fallback to single chunk")
        return [clean_text]


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
        
    except ImportError:
        logger.error("Semchunk not installed, using simple splitting")
        # Fallback: simple token-based splitting
        return _fallback_chunk(semantic_blocks, target_tokens, overlap_tokens)


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


def validate_chunk_size(chunk_text: str, max_tokens: int = 8192) -> bool:
    """
    Validate that chunk doesn't exceed embedding model's token limit.
    
    Args:
        chunk_text: Chunk text to validate
        max_tokens: Maximum allowed tokens (nomic-embed-text: 8192)
        
    Returns:
        True if chunk is within limits
    """
    token_count = count_tokens(chunk_text)
    return token_count <= max_tokens


def filter_chunks(
    chunks: list[dict],
    min_tokens: int = 50,
    max_tokens: int = 8192
) -> list[dict]:
    """
    Filter chunks by token count.
    
    Args:
        chunks: List of chunk dictionaries
        min_tokens: Minimum token count (discard too short)
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
