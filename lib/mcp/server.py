#!/usr/bin/env python3
"""
Server MCP per Ragify - Query semantica della documentazione.
Riutilizza il codice esistente di lib/ per embedding e Qdrant.
"""

import os
import sys
from collections import Counter
from pathlib import Path

# Add parent to path to import lib modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.server.fastmcp import FastMCP

# Configuration
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')

# Set OLLAMA_URL for embedding module
os.environ['OLLAMA_URL'] = OLLAMA_URL

# Server MCP
mcp = FastMCP(name="ragify")


def _get_client():
    """Get Qdrant client instance."""
    from qdrant_client import QdrantClient
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


@mcp.tool()
def search_documentation(
    query: str,
    collection: str = "documentation",
    limit: int = 5
) -> str:
    """
    Cerca nella documentazione indicizzata con ricerca semantica.

    Args:
        query: Testo della query di ricerca
        collection: Nome della collection Qdrant (default: documentation)
        limit: Numero massimo di risultati (default: 5)

    Returns:
        Risultati formattati della ricerca
    """
    from lib.embedding import get_embedding

    # Generate embedding for query
    embedding = get_embedding(query, timeout=30, max_retries=2)
    if not embedding:
        return "Errore: Ollama non raggiungibile o embedding fallito. Verifica che Ollama sia in esecuzione."

    try:
        client = _get_client()

        # Check if collection exists
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if collection not in collection_names:
            available = ', '.join(collection_names) if collection_names else 'nessuna'
            return f"Errore: Collection '{collection}' non esiste. Collection disponibili: {available}"

        # Search
        results = client.query_points(
            collection_name=collection,
            query=embedding,
            limit=limit,
            with_payload=True
        ).points

        if not results:
            return f"Nessun risultato trovato per '{query}' nella collection '{collection}'"

        # Format output
        output = [f"Trovati {len(results)} risultati in '{collection}':\n"]

        for i, r in enumerate(results, 1):
            p = r.payload
            output.append(f"[{i}] Score: {r.score:.4f}")
            output.append(f"   File: {p.get('url', 'N/A')}")
            output.append(f"   Titolo: {p.get('title', 'N/A')}")
            text = p.get('text', '')
            # Truncate long text
            if len(text) > 500:
                text = text[:500] + "..."
            output.append(f"   Contenuto: {text}")
            output.append("")

        return "\n".join(output)

    except Exception as e:
        return f"Errore durante la ricerca: {e}"


@mcp.tool()
def list_collections() -> str:
    """
    Elenca tutte le collection Qdrant disponibili.

    Returns:
        Lista delle collection con informazioni sui punti
    """
    try:
        client = _get_client()
        collections = client.get_collections().collections

        if not collections:
            return "Nessuna collection trovata in Qdrant"

        output = [f"Collection disponibili ({len(collections)}):\n"]

        for c in collections:
            try:
                info = client.get_collection(c.name)
                output.append(f"- {c.name}: {info.points_count} punti")
            except Exception:
                output.append(f"- {c.name}: (info non disponibile)")

        return "\n".join(output)

    except Exception as e:
        return f"Errore nel recupero delle collection: {e}"


@mcp.tool()
def list_sources(collection: str = "documentation") -> str:
    """
    Elenca i file indicizzati in una collection.

    Args:
        collection: Nome della collection (default: documentation)

    Returns:
        Lista dei file con conteggio chunks
    """
    try:
        client = _get_client()

        # Check if collection exists
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if collection not in collection_names:
            available = ', '.join(collection_names) if collection_names else 'nessuna'
            return f"Errore: Collection '{collection}' non esiste. Collection disponibili: {available}"

        # Scroll all points to count sources
        sources = Counter()
        offset = None

        while True:
            points, next_offset = client.scroll(
                collection_name=collection,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

            if not points:
                break

            for p in points:
                url = p.payload.get('url', 'N/A')
                sources[url] += 1

            if next_offset is None:
                break
            offset = next_offset

        if not sources:
            return f"Collection '{collection}' vuota"

        # Format output
        total_chunks = sum(sources.values())
        output = [f"File in '{collection}' ({len(sources)} file, {total_chunks} chunk totali):\n"]

        for url, count in sorted(sources.items()):
            # Shorten long paths
            name = Path(url).name if len(url) > 60 else url
            output.append(f"- {name} ({count} chunk)")

        return "\n".join(output)

    except Exception as e:
        return f"Errore nel recupero delle sorgenti: {e}"


if __name__ == "__main__":
    mcp.run()
