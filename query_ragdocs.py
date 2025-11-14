#!/usr/bin/env python3
import requests
import json
import sys

query = sys.argv[1] if len(sys.argv) > 1 else "finalizeFlow"
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5

# Generate embedding
ollama_response = requests.post(
    "http://localhost:11434/api/embeddings",
    json={"model": "nomic-embed-text", "prompt": query}
)
query_embedding = ollama_response.json()["embedding"]

# Search Qdrant
qdrant_response = requests.post(
    "http://127.0.0.1:6333/collections/documentation/points/search",
    json={"vector": query_embedding, "limit": limit, "with_payload": True}
)

results = qdrant_response.json()["result"]

for i, result in enumerate(results, 1):
    score = result.get("score", 0)
    payload = result.get("payload", {})
    print(f"\n[{i}] Score: {score:.4f}")
    print(f"Title: {payload.get('title', 'Unknown')}")
    print(f"URL: {payload.get('url', 'Unknown')}")
    print(f"\nContent:\n{payload.get('text', '')[:800]}...\n")
    print("-" * 80)
