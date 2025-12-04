#!/usr/bin/env python3
"""
Configuration management with Pydantic validation.
Provides schema validation and merging of config sources (file, env, CLI).
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class ExtractionConfig(BaseModel):
    """Configuration for text extraction."""

    tika_jar_path: str = Field(default="auto", description="Path to Tika JAR or 'auto' for auto-download")
    timeout: int = Field(default=60, description="Extraction timeout in seconds")
    max_file_size: int = Field(default=100 * 1024 * 1024, description="Maximum file size in bytes")


class ChunkingConfig(BaseModel):
    """Configuration for text chunking (single-pass semchunk)."""

    chunk_size: int = Field(default=512, description="Target chunk size in tokens")
    overlap: int = Field(default=50, description="Overlap between chunks in tokens")
    max_tokens: int = Field(default=2048, description="Maximum tokens per chunk (nomic-embed-text limit)")


class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation."""

    provider: str = Field(default="ollama", description="Embedding provider")
    model: str = Field(default="nomic-embed-text", description="Embedding model name")
    batch_size: int = Field(default=32, description="Batch size for embedding (optimized)")
    url: Optional[str] = Field(default=None, description="Ollama/API URL")

    @field_validator('url')
    def set_url_from_env(cls, v):
        """Set URL from environment if not provided."""
        if v is None:
            return os.getenv('OLLAMA_URL', 'http://localhost:11434')
        return v


def _get_qdrant_url():
    return os.getenv('QDRANT_URL', 'http://localhost:6333')

def _get_qdrant_api_key():
    return os.getenv('QDRANT_API_KEY')

class QdrantConfig(BaseModel):
    """Configuration for Qdrant vector database."""

    collection: str = Field(default="documentation", description="Collection name")
    batch_size: int = Field(default=100, description="Batch upload size (optimized)")
    url: str = Field(default_factory=_get_qdrant_url, description="Qdrant URL")
    api_key: Optional[str] = Field(default_factory=_get_qdrant_api_key, description="API key if required")


class ProcessingConfig(BaseModel):
    """Configuration for file processing."""

    skip_hidden: bool = Field(default=True, description="Skip hidden files/directories")
    skip_patterns: List[str] = Field(
        default_factory=lambda: ["*.pyc", "*.exe", "__pycache__", ".git", "node_modules"],
        description="Glob patterns to skip"
    )
    extensions_filter: Optional[List[str]] = Field(
        default=None,
        description="If provided, only process files with these extensions"
    )


class OutputConfig(BaseModel):
    """Configuration for output and reporting."""

    report_format: str = Field(default="markdown", description="Report format (markdown, json, html)")
    report_path: Path = Field(default=Path("./ragify_report.md"), description="Report output path")
    verbose: bool = Field(default=False, description="Verbose output")


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    format: str = Field(default="json", description="Log format (json, text)")
    level: str = Field(default="info", description="Log level")
    file: Optional[Path] = Field(default=Path("./ragify.log"), description="Log file path")


class RagifyConfig(BaseModel):
    """Main configuration for Ragify pipeline."""

    version: str = Field(default="1.0", description="Config version")
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    def save(self, path: Path):
        """Save configuration to file."""
        path = Path(path)
        content = self.model_dump(exclude_none=True)

        if path.suffix == '.json':
            with open(path, 'w') as f:
                json.dump(content, f, indent=2)
        else:  # Default to YAML
            with open(path, 'w') as f:
                yaml.dump(content, f, default_flow_style=False)

        logger.info(f"Configuration saved to {path}")

    @classmethod
    def load(cls, path: Optional[Path] = None) -> 'RagifyConfig':
        """
        Load configuration from file, merging with environment variables.

        Args:
            path: Path to config file (YAML or JSON)

        Returns:
            Loaded configuration
        """
        config_data = {}

        # Load from file if provided
        if path and Path(path).exists():
            path = Path(path)
            logger.info(f"Loading configuration from {path}")

            with open(path, 'r') as f:
                if path.suffix == '.json':
                    config_data = json.load(f)
                else:  # Default to YAML
                    config_data = yaml.safe_load(f) or {}

        # Create config with file data and env overrides
        config = cls(**config_data)

        # Apply environment variable overrides
        config = apply_env_overrides(config)

        return config

    @classmethod
    def default(cls) -> 'RagifyConfig':
        """Get default configuration."""
        return cls()


def apply_env_overrides(config: RagifyConfig) -> RagifyConfig:
    """
    Apply environment variable overrides to configuration.

    Environment variables format: RAGIFY_<SECTION>_<KEY>
    Example: RAGIFY_EMBEDDING_MODEL=gpt-3.5-turbo
    """
    env_prefix = "RAGIFY_"

    for key, value in os.environ.items():
        if not key.startswith(env_prefix):
            continue

        # Parse environment variable
        parts = key[len(env_prefix):].lower().split('_')

        if len(parts) < 2:
            continue

        section = parts[0]
        field = '_'.join(parts[1:])

        # Apply override
        try:
            if hasattr(config, section):
                section_obj = getattr(config, section)
                if hasattr(section_obj, field):
                    # Convert value type based on field type
                    current_value = getattr(section_obj, field)
                    if isinstance(current_value, bool):
                        new_value = value.lower() in ('true', '1', 'yes')
                    elif isinstance(current_value, int):
                        new_value = int(value)
                    elif isinstance(current_value, float):
                        new_value = float(value)
                    elif isinstance(current_value, list):
                        new_value = value.split(',')
                    else:
                        new_value = value

                    setattr(section_obj, field, new_value)
                    logger.debug(f"Override from env: {section}.{field} = {new_value}")

        except Exception as e:
            logger.warning(f"Failed to apply env override {key}: {e}")

    return config


def merge_cli_args(config: RagifyConfig, args: dict) -> RagifyConfig:
    """
    Merge CLI arguments into configuration.

    Args:
        config: Base configuration
        args: CLI arguments dictionary

    Returns:
        Updated configuration
    """
    # Map common CLI args to config paths
    cli_mapping = {
        'chunk_size': ('chunking', 'chunk_size'),
        'overlap': ('chunking', 'overlap'),
        'batch_size': ('embedding', 'batch_size'),
        'collection': ('qdrant', 'collection'),
        'verbose': ('output', 'verbose'),
        'log_level': ('logging', 'level'),
    }

    for cli_key, (section, field) in cli_mapping.items():
        if cli_key in args and args[cli_key] is not None:
            section_obj = getattr(config, section)
            setattr(section_obj, field, args[cli_key])
            logger.debug(f"CLI override: {section}.{field} = {args[cli_key]}")

    return config


# Default configuration template
DEFAULT_CONFIG_YAML = """
# Ragify Configuration File

ragify:
  version: "1.0"

extraction:
  tika_jar_path: auto  # auto-download or path to Tika JAR
  timeout: 60
  max_file_size: 104857600  # 100MB

chunking:
  # Single-pass semantic chunking with semchunk
  chunk_size: 512
  overlap: 50
  max_tokens: 2048

embedding:
  provider: ollama
  model: nomic-embed-text  # Configurable via EMBEDDING_MODEL env
  batch_size: 32  # Optimized for throughput
  # url: http://localhost:11434  # Defaults from env OLLAMA_URL

qdrant:
  collection: documentation
  batch_size: 100  # Optimized for throughput
  # url: http://localhost:6333  # Defaults from env QDRANT_URL
  # api_key: null  # Defaults from env QDRANT_API_KEY

processing:
  skip_hidden: true
  skip_patterns:
    - "*.pyc"
    - "*.exe"
    - "__pycache__"
    - ".git"
    - "node_modules"
    - ".venv"
    - "venv"

output:
  report_format: markdown
  report_path: ./ragify_report.md
  verbose: false

logging:
  format: json
  level: info
  file: ./ragify.log
"""


def create_default_config(path: Path = Path("config.yaml")):
    """Create default configuration file."""
    with open(path, 'w') as f:
        f.write(DEFAULT_CONFIG_YAML.strip())
    logger.info(f"Created default configuration at {path}")
    return path