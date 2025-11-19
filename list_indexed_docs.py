#!/usr/bin/env python3
"""
List all documents indexed in Qdrant.
Shows unique URLs and chunk counts.
"""

from qdrant_client import QdrantClient
from collections import Counter

QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "documentation"


def list_indexed_documents():
    """List all indexed documents with statistics."""
    client = QdrantClient(url=QDRANT_URL)
    
    # Get collection info
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"❌ Error connecting to Qdrant: {e}")
        return
    
    print("=" * 80)
    print(f"📊 DOCUMENTI INDICIZZATI - Collezione '{COLLECTION_NAME}'")
    print("=" * 80)
    print(f"\n📦 Statistiche generali:")
    print(f"   Totale chunks: {collection.points_count}")
    print(f"   Dimensione vettori: {collection.config.params.vectors.size}")
    
    # Scroll all points to get URLs
    print(f"\n🔍 Caricamento documenti...")
    
    urls_chunks = Counter()
    offset = None
    
    while True:
        results = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        points, next_offset = results
        
        if not points:
            break
        
        for point in points:
            url = point.payload.get('url', 'N/A')
            urls_chunks[url] += 1
        
        if next_offset is None:
            break
        offset = next_offset
    
    # Display results
    print(f"\n📄 Documenti unici: {len(urls_chunks)}")
    print("\n" + "=" * 80)
    print(f"{'#':<5} {'Chunks':<10} {'URL'}")
    print("=" * 80)
    
    for i, (url, chunk_count) in enumerate(sorted(urls_chunks.items()), 1):
        # Shorten URL for display
        display_url = url.replace('http://localhost:8000/', '')
        print(f"{i:<5} {chunk_count:<10} {display_url}")
    
    print("=" * 80)
    print(f"\n✅ Totale: {len(urls_chunks)} documenti, {sum(urls_chunks.values())} chunks")
    print()


if __name__ == "__main__":
    list_indexed_documents()
