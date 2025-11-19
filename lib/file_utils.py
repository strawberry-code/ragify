#!/usr/bin/env python3
"""
File utilities for hash-based deduplication and tracking.
Provides efficient file hashing and change detection for incremental updates.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional, Set

logger = logging.getLogger(__name__)


def compute_file_hash(file_path: Path, algorithm: str = 'sha256', chunk_size: int = 8192) -> str:
    """
    Compute hash of file content for deduplication.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm to use (sha256, md5, sha1)
        chunk_size: Size of chunks to read (for large files)

    Returns:
        Hex digest of file hash
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if algorithm == 'sha256':
        hasher = hashlib.sha256()
    elif algorithm == 'md5':
        hasher = hashlib.md5()
    elif algorithm == 'sha1':
        hasher = hashlib.sha1()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)

        file_hash = hasher.hexdigest()
        logger.debug(f"Computed {algorithm} hash for {file_path.name}: {file_hash[:16]}...")
        return file_hash

    except Exception as e:
        logger.error(f"Failed to compute hash for {file_path}: {e}")
        raise


def check_if_changed(file_path: Path, stored_hash: str, algorithm: str = 'sha256') -> bool:
    """
    Check if file has changed by comparing hashes.

    Args:
        file_path: Path to file
        stored_hash: Previously stored hash
        algorithm: Hash algorithm to use

    Returns:
        True if file has changed, False otherwise
    """
    try:
        current_hash = compute_file_hash(file_path, algorithm)
        has_changed = current_hash != stored_hash

        if has_changed:
            logger.info(f"File changed: {file_path.name}")
        else:
            logger.debug(f"File unchanged: {file_path.name}")

        return has_changed

    except Exception as e:
        logger.error(f"Error checking file change for {file_path}: {e}")
        # If we can't determine, assume it changed to be safe
        return True


def get_file_metadata(file_path: Path) -> dict:
    """
    Get basic file metadata for tracking.

    Args:
        file_path: Path to file

    Returns:
        Dictionary with file metadata
    """
    stat = file_path.stat()
    return {
        'size': stat.st_size,
        'mtime': stat.st_mtime,
        'ctime': stat.st_ctime,
        'extension': file_path.suffix.lower(),
        'name': file_path.name,
    }


def scan_directory(
    root_path: Path,
    skip_hidden: bool = True,
    skip_patterns: Optional[Set[str]] = None,
    extensions_filter: Optional[Set[str]] = None
) -> list[Path]:
    """
    Recursively scan directory for files to process.

    Args:
        root_path: Root directory to scan
        skip_hidden: Skip hidden files/directories (starting with .)
        skip_patterns: Set of glob patterns to skip (e.g., {'*.pyc', '__pycache__'})
        extensions_filter: If provided, only include files with these extensions

    Returns:
        List of file paths to process
    """
    root_path = Path(root_path).resolve()

    if not root_path.exists():
        raise FileNotFoundError(f"Directory not found: {root_path}")

    if not root_path.is_dir():
        raise ValueError(f"Not a directory: {root_path}")

    skip_patterns = skip_patterns or {
        '*.pyc', '*.pyo', '*.pyd',  # Python compiled
        '*.so', '*.dll', '*.dylib',  # Binary libraries
        '*.exe', '*.app',  # Executables
        '__pycache__', '.git', '.svn',  # VCS and cache
        'node_modules', 'venv', '.venv',  # Dependencies
        '*.log', '*.tmp', '*.temp',  # Temporary files
    }

    files = []

    for path in root_path.rglob('*'):
        # Skip directories
        if path.is_dir():
            continue

        # Skip hidden files if requested
        if skip_hidden and any(part.startswith('.') for part in path.parts):
            logger.debug(f"Skipping hidden: {path}")
            continue

        # Skip by pattern
        should_skip = False
        for pattern in skip_patterns:
            if path.match(pattern):
                logger.debug(f"Skipping pattern {pattern}: {path}")
                should_skip = True
                break

        if should_skip:
            continue

        # Filter by extension if specified
        if extensions_filter and path.suffix.lower() not in extensions_filter:
            logger.debug(f"Skipping extension {path.suffix}: {path}")
            continue

        files.append(path)

    logger.info(f"Found {len(files)} files to process in {root_path}")
    return sorted(files)  # Sort for consistent ordering


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


class FileHashCache:
    """
    In-memory cache for file hashes during a processing run.
    """

    def __init__(self):
        self.cache = {}

    def get(self, file_path: Path) -> Optional[str]:
        """Get cached hash for file."""
        return self.cache.get(str(file_path))

    def set(self, file_path: Path, file_hash: str):
        """Cache hash for file."""
        self.cache[str(file_path)] = file_hash

    def has(self, file_path: Path) -> bool:
        """Check if file hash is cached."""
        return str(file_path) in self.cache

    def clear(self):
        """Clear all cached hashes."""
        self.cache.clear()

    def size(self) -> int:
        """Get number of cached hashes."""
        return len(self.cache)