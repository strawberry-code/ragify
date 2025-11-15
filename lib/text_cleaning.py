#!/usr/bin/env python3
"""
Text cleaning utilities for RAG pipeline.
Prepares raw text for semantic chunking.
"""

import re
import unicodedata
from typing import Optional


def clean_text(raw_text: str) -> str:
    """
    Comprehensive text cleaning pipeline.
    
    Steps:
    1. Unicode normalization (NFC)
    2. Remove control characters
    3. Normalize whitespace
    4. Unify newlines
    5. Remove excessive blank lines
    
    Args:
        raw_text: Raw text from HTML extraction or other source
        
    Returns:
        Cleaned text ready for chunking
    """
    if not raw_text:
        return ""
    
    # 1. Normalize unicode to NFC form
    text = unicodedata.normalize('NFC', raw_text)
    
    # 2. Remove control characters (except newline, tab)
    text = ''.join(c for c in text if c.isprintable() or c in '\n\t')
    
    # 3. Normalize whitespace (collapse multiple spaces)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 4. Normalize tabs to spaces
    text = text.replace('\t', ' ')
    
    # 5. Remove spaces at line boundaries
    lines = [line.strip() for line in text.splitlines()]
    text = '\n'.join(lines)
    
    # 6. Collapse excessive newlines (max 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 7. Final trim
    text = text.strip()
    
    return text


def remove_boilerplate(text: str, patterns: Optional[list[str]] = None) -> str:
    """
    Remove common boilerplate patterns from text.
    
    Args:
        text: Cleaned text
        patterns: Optional list of regex patterns to remove
        
    Returns:
        Text with boilerplate removed
    """
    if patterns is None:
        # Default boilerplate patterns
        patterns = [
            r'Copyright \(c\) \d{4}.*',
            r'All rights reserved\..*',
            r'Terms of Service.*',
            r'Privacy Policy.*',
            r'Cookie Policy.*',
        ]
    
    result = text
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE | re.MULTILINE)
    
    return result


def validate_text_quality(text: str, min_length: int = 50) -> bool:
    """
    Validate if text is worth processing.
    
    Args:
        text: Text to validate
        min_length: Minimum character count
        
    Returns:
        True if text meets quality criteria
    """
    if not text or len(text.strip()) < min_length:
        return False
    
    # Check if text has reasonable character diversity
    # (not just repeated characters or gibberish)
    unique_chars = len(set(text.lower()))
    if unique_chars < 10:
        return False
    
    # Check for minimum word count
    words = text.split()
    if len(words) < 10:
        return False
    
    return True
