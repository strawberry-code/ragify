"""
Embedding generation via Ollama - standalone module for ragify-mcp package.
"""

import os
import requests

OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')


def get_embedding(
    text: str,
    model: str = "nomic-embed-text",
    timeout: int = 30,
    max_retries: int = 2
) -> list[float] | None:
    """
    Generate embedding using Ollama.

    Args:
        text: Text to embed
        model: Ollama embedding model (default: nomic-embed-text)
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        Embedding vector or None if failed
    """
    url = f"{OLLAMA_URL}/api/embeddings"

    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                json={"model": model, "prompt": text},
                timeout=timeout
            )
            response.raise_for_status()
            return response.json().get("embedding")
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                continue
            return None
        except Exception:
            return None

    return None
