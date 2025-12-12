#!/usr/bin/env python3
"""
Text extraction system using Apache Tika server.
Tika is always required and runs as a server for optimal performance.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Protocol

logger = logging.getLogger(__name__)


class TextExtractor(Protocol):
    """Protocol for text extractors."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if this extractor can handle the file type."""
        ...

    def extract(self, file_path: Path) -> Tuple[str, Dict]:
        """Extract text and metadata from file."""
        ...


class ExtractorRegistry:
    """Registry for managing text extractors."""

    def __init__(self):
        self.extractors = []
        self._tika_extractor = None

    def register(self, extractor: TextExtractor):
        """Register a new extractor."""
        self.extractors.append(extractor)

    def get_extractor(self, file_path: Path) -> Optional[TextExtractor]:
        """Get appropriate extractor for file type."""
        # Try specific extractors first (PlainText, Code - più veloci per file semplici)
        for extractor in self.extractors:
            if extractor.can_handle(file_path):
                return extractor

        # Fallback to Tika server (sempre disponibile)
        if self._tika_extractor is None:
            try:
                from .tika_extractor import TikaExtractor
                self._tika_extractor = TikaExtractor()
            except Exception as e:
                logger.error(f"Failed to initialize Tika: {e}")
                return None

        return self._tika_extractor

    def extract(self, file_path: Path) -> Tuple[str, Dict]:
        """Extract text and metadata from any file."""
        extractor = self.get_extractor(file_path)

        if extractor is None:
            logger.warning(f"Cannot extract: {file_path.name} (no suitable extractor)")
            return "", {"error": "No suitable extractor", "file_path": str(file_path)}

        logger.debug(f"Using {extractor.__class__.__name__} for {file_path}")
        return extractor.extract(file_path)


# Global registry instance
registry = ExtractorRegistry()

# Register optimized extractors (faster than Tika for simple files)
try:
    from .tika_extractor import PlainTextExtractor, CodeExtractor
    registry.register(PlainTextExtractor())
    registry.register(CodeExtractor())
except ImportError:
    logger.warning("Optimized extractors not available")


def extract_file_content(file_path: Path) -> Tuple[str, Dict]:
    """
    Main entry point for file content extraction.

    Args:
        file_path: Path to file to extract

    Returns:
        Tuple of (text_content, metadata_dict)
    """
    return registry.extract(file_path)


def set_tika_enabled(enabled: bool):
    """
    Legacy function for compatibility - Tika is always enabled.

    Args:
        enabled: Ignored (Tika always active via server)
    """
    # Tika server è sempre attivo, questa funzione esiste solo per compatibilità
    if not enabled:
        logger.warning("set_tika_enabled(False) ignored - Tika server is always active")