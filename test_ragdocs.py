#!/usr/bin/env python3
"""
Test ragdocs - Query the ragdocs vector database
"""

import requests
import json
import argparse


def query_ragdocs(query, limit=5, qdrant_url="http://127.0.0.1:6333",
                  collection_name="documentation", ollama_url="http://localhost:11434"):
    """
    Query the ragdocs vector database directly

    Args:
        query: The search query
        limit: Maximum number of results to return
        qdrant_url: URL of the Qdrant instance
        collection_name: Name of the Qdrant collection
        ollama_url: URL of the Ollama instance

    Returns:
        Search results
    """
    print(f"Querying ragdocs with: '{query}'")
    print("-" * 80)

    # Step 1: Generate embedding for the query using Ollama
    print("Generating embedding for query...")

    ollama_response = requests.post(
        f"{ollama_url}/api/embeddings",
        json={
            "model": "nomic-embed-text",
            "prompt": query
        }
    )

    if ollama_response.status_code != 200:
        raise Exception(f"Failed to generate embedding: {ollama_response.text}")

    query_embedding = ollama_response.json()["embedding"]
    print(f"✓ Generated embedding (dimension: {len(query_embedding)})")

    # Step 2: Search in Qdrant
    print(f"Searching in Qdrant collection '{collection_name}'...")

    qdrant_response = requests.post(
        f"{qdrant_url}/collections/{collection_name}/points/search",
        json={
            "vector": query_embedding,
            "limit": limit,
            "with_payload": True
        }
    )

    if qdrant_response.status_code != 200:
        raise Exception(f"Failed to search Qdrant: {qdrant_response.text}")

    results = qdrant_response.json()["result"]
    print(f"✓ Found {len(results)} results\n")

    # Step 3: Display results
    print("=" * 80)
    print("SEARCH RESULTS")
    print("=" * 80)

    if not results:
        print("No results found.")
        return []

    for i, result in enumerate(results, 1):
        score = result.get("score", 0)
        payload = result.get("payload", {})

        title = payload.get("title", "Unknown")
        url = payload.get("url", "Unknown")
        text = payload.get("text", "")

        print(f"\n[{i}] Score: {score:.4f}")
        print(f"Title: {title}")
        print(f"URL: {url}")
        print(f"\nContent:\n{text[:500]}...")
        print("-" * 80)

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Query the ragdocs vector database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search with default query
  python test_ragdocs.py

  # Search with custom query
  python test_ragdocs.py --query "What is a CorDapp?"

  # Get more results
  python test_ragdocs.py --query "flow framework" --limit 10

  # Use different Qdrant instance
  python test_ragdocs.py --qdrant-url http://localhost:6333
        """
    )
    parser.add_argument('--query', '-q',
                       default='cosa fa la funzione finalizeFlow() ?',
                       help='Search query (default: "cosa fa la funzione finalizeFlow() ?")')
    parser.add_argument('--limit', '-l', type=int, default=5,
                       help='Maximum number of results (default: 5)')
    parser.add_argument('--qdrant-url', default='http://127.0.0.1:6333',
                       help='Qdrant URL (default: http://127.0.0.1:6333)')
    parser.add_argument('--collection', default='documentation',
                       help='Collection name (default: documentation)')
    parser.add_argument('--ollama-url', default='http://localhost:11434',
                       help='Ollama URL (default: http://localhost:11434)')

    args = parser.parse_args()

    try:
        query_ragdocs(
            query=args.query,
            limit=args.limit,
            qdrant_url=args.qdrant_url,
            collection_name=args.collection,
            ollama_url=args.ollama_url
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)


if __name__ == '__main__':
    main()
