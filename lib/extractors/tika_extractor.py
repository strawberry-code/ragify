#!/usr/bin/env python3
"""
Apache Tika-based universal text extractor.
Handles all file formats through Tika's powerful extraction capabilities.
"""

import logging
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Optional: try importing tika
try:
    from tika import parser as tika_parser
    from tika import tika
    # Configure Tika to auto-download if needed
    tika.TikaClientOnly = False
    TIKA_AVAILABLE = True
except ImportError:
    logger.warning("Apache Tika not available, using fallback extractors only")
    TIKA_AVAILABLE = False


class TikaExtractor:
    """Universal file extractor using Apache Tika."""

    def __init__(self, timeout: int = 60, max_file_size: int = 100 * 1024 * 1024):
        """
        Initialize Tika extractor.

        Args:
            timeout: Extraction timeout in seconds
            max_file_size: Maximum file size in bytes (default 100MB)
        """
        self.timeout = timeout
        self.max_file_size = max_file_size

        if not TIKA_AVAILABLE:
            raise ImportError("Apache Tika is required but not installed. Run: pip install tika")

    def can_handle(self, file_path: Path) -> bool:
        """Tika can handle any file type."""
        return file_path.is_file()

    def extract(self, file_path: Path) -> Tuple[str, Dict]:
        """
        Extract text and metadata from file using Tika.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (text_content, metadata_dict)
        """
        file_path = Path(file_path).resolve()

        # Check file size
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size:
            logger.warning(f"File too large ({file_size} bytes): {file_path}")
            return "", {"error": "File too large", "size": file_size}

        try:
            # Use memory mapping for large files
            if file_size > 10 * 1024 * 1024:  # 10MB threshold
                logger.info(f"Using memory-mapped extraction for large file: {file_path}")
                return self._extract_with_mmap(file_path)

            # Standard extraction for smaller files
            logger.debug(f"Extracting content from: {file_path}")

            # Parse with Tika
            # Only use serverEndpoint if explicitly set
            server_endpoint = os.getenv('TIKA_SERVER_ENDPOINT')
            if server_endpoint:
                parsed = tika_parser.from_file(
                    str(file_path),
                    serverEndpoint=server_endpoint,
                    requestOptions={'timeout': self.timeout}
                )
            else:
                # Use local JAR (auto-downloaded)
                parsed = tika_parser.from_file(
                    str(file_path),
                    requestOptions={'timeout': self.timeout}
                )

            # Extract text
            text = parsed.get('content', '').strip()

            # Extract and process metadata
            raw_metadata = parsed.get('metadata', {})
            metadata = self._process_metadata(raw_metadata, file_path)

            logger.info(f"Extracted {len(text)} characters from {file_path.name}")

            return text, metadata

        except Exception as e:
            logger.error(f"Tika extraction failed for {file_path}: {e}")
            # Return empty text with error metadata
            return "", {
                "error": str(e),
                "file_path": str(file_path),
                "file_name": file_path.name
            }

    def _extract_with_mmap(self, file_path: Path) -> Tuple[str, Dict]:
        """
        Extract using memory mapping for large files.

        Args:
            file_path: Path to large file

        Returns:
            Tuple of (text_content, metadata_dict)
        """
        import mmap

        try:
            with open(file_path, 'rb') as f:
                # Memory map the file
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                    # Tika can work with file path directly
                    # Memory mapping helps with system resource management
                    server_endpoint = os.getenv('TIKA_SERVER_ENDPOINT')
                    if server_endpoint:
                        parsed = tika_parser.from_file(
                            str(file_path),
                            serverEndpoint=server_endpoint,
                            requestOptions={'timeout': self.timeout}
                        )
                    else:
                        parsed = tika_parser.from_file(
                            str(file_path),
                            requestOptions={'timeout': self.timeout}
                        )

                    text = parsed.get('content', '').strip()
                    raw_metadata = parsed.get('metadata', {})
                    metadata = self._process_metadata(raw_metadata, file_path)

                    return text, metadata

        except Exception as e:
            logger.error(f"Memory-mapped extraction failed for {file_path}: {e}")
            return "", {"error": str(e), "file_path": str(file_path)}

    def _process_metadata(self, raw_metadata: Dict, file_path: Path) -> Dict:
        """
        Process and normalize Tika metadata.

        Args:
            raw_metadata: Raw metadata from Tika
            file_path: Original file path

        Returns:
            Processed metadata dictionary
        """
        # Start with file system metadata
        stat = file_path.stat()
        metadata = {
            'file_path': str(file_path),
            'file_name': file_path.name,
            'file_size': stat.st_size,
            'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }

        # Add useful Tika metadata if available
        if raw_metadata:
            # Title
            for key in ['title', 'dc:title', 'Title']:
                if key in raw_metadata:
                    metadata['title'] = raw_metadata[key]
                    break

            # Author
            for key in ['author', 'dc:creator', 'Author', 'meta:author']:
                if key in raw_metadata:
                    metadata['author'] = raw_metadata[key]
                    break

            # Content type
            if 'Content-Type' in raw_metadata:
                metadata['content_type'] = raw_metadata['Content-Type']

            # Language
            if 'language' in raw_metadata:
                metadata['language'] = raw_metadata['language']

            # Page count (for PDFs)
            if 'xmpTPg:NPages' in raw_metadata:
                metadata['page_count'] = raw_metadata['xmpTPg:NPages']

            # Word count
            if 'meta:word-count' in raw_metadata:
                metadata['word_count'] = raw_metadata['meta:word-count']

        # Guess content type from extension if not detected
        if 'content_type' not in metadata:
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type:
                metadata['content_type'] = mime_type

        return metadata


class PlainTextExtractor:
    """Optimized extractor for plain text files."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if file is plain text."""
        suffixes = {
            '.txt', '.md', '.rst', '.log', '.csv',
            '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg',
            '.mod', '.sum',  # Go modules
            '.lock', '.gitignore', '.gitattributes',  # Config files
            '.env', '.properties',  # Config
            'Makefile', 'Dockerfile', 'LICENSE', 'README'  # Common files without extension
        }
        # Check extension or full filename
        return (file_path.suffix.lower() in suffixes or
                file_path.name in suffixes)

    def extract(self, file_path: Path) -> Tuple[str, Dict]:
        """Extract content from plain text file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

            metadata = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'file_size': file_path.stat().st_size,
                'content_type': 'text/plain',
            }

            return text, metadata

        except Exception as e:
            logger.error(f"Failed to extract text from {file_path}: {e}")
            return "", {"error": str(e), "file_path": str(file_path)}


class CodeExtractor:
    """Optimized extractor for source code files."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if file is source code."""
        code_extensions = {
            '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.hpp',
            '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
            '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd'
        }
        return file_path.suffix.lower() in code_extensions

    def extract(self, file_path: Path) -> Tuple[str, Dict]:
        """Extract content from source code file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

            # Detect programming language
            language = self._detect_language(file_path)

            metadata = {
                'file_path': str(file_path),
                'file_name': file_path.name,
                'file_size': file_path.stat().st_size,
                'content_type': f'text/x-{language}',
                'language': language,
            }

            # Count lines of code
            lines = text.splitlines()
            metadata['line_count'] = len(lines)
            metadata['non_empty_lines'] = sum(1 for line in lines if line.strip())

            return text, metadata

        except Exception as e:
            logger.error(f"Failed to extract code from {file_path}: {e}")
            return "", {"error": str(e), "file_path": str(file_path)}

    def _detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.sh': 'shell',
            '.bash': 'bash',
        }
        return ext_to_lang.get(file_path.suffix.lower(), 'unknown')