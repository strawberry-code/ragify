#!/usr/bin/env python3
"""
Script per aggiungere documentazione da URL a Qdrant.
Legge URL da un file (una per riga) e li indicizza in Qdrant usando Ollama.
"""

import requests
from bs4 import BeautifulSoup
import sys
from urllib.parse import urlparse
import uuid
from datetime import datetime

# Configurazione
QDRANT_URL = "http://localhost:6333"
OLLAMA_URL = "http://localhost:11434"
COLLECTION_NAME = "documentation"
CHUNK_SIZE = 1000  # Caratteri per chunk
CHUNK_OVERLAP = 200  # Overlap tra chunks
BATCH_SIZE = 10  # Numero di punti da caricare per batch

def get_embedding(text):
    """Genera embedding usando Ollama con nomic-embed-text"""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": text
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        print(f"   ❌ Errore generazione embedding: {e}")
        return None

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Divide il testo in chunks con overlap"""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # Prova a terminare il chunk su un punto o newline
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            if break_point > chunk_size * 0.7:  # Solo se non troppo indietro
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1

        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if c]  # Rimuovi chunks vuoti

def fetch_url_content(url):
    """Scarica e pulisce il contenuto HTML da URL"""
    try:
        print(f"   📥 Scaricando: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Rimuovi script, style, etc
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        # Estrai testo
        text = soup.get_text(separator='\n', strip=True)

        # Pulisci spazi multipli
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = '\n'.join(lines)

        # Estrai titolo
        title = soup.find('title')
        title_text = title.get_text().strip() if title else url

        return text, title_text
    except Exception as e:
        print(f"   ❌ Errore download: {e}")
        return None, None

def add_to_qdrant(url, text, title):
    """Aggiunge il contenuto a Qdrant"""
    try:
        # Chunka il testo
        chunks = chunk_text(text)
        print(f"   ✂️  Creati {len(chunks)} chunks")

        # Prepara punti per Qdrant
        points = []
        for i, chunk in enumerate(chunks):
            print(f"   🔢 Processando chunk {i+1}/{len(chunks)}...", end='\r')

            # Genera embedding
            vector = get_embedding(chunk)
            if vector is None:
                continue

            # Crea punto
            point = {
                "id": str(uuid.uuid4()),
                "vector": vector,
                "payload": {
                    "_type": "DocumentChunk",
                    "text": chunk,
                    "url": url,
                    "title": title,
                    "timestamp": datetime.now().isoformat(),
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            }
            points.append(point)

            # Upload batch
            if len(points) >= BATCH_SIZE:
                upload_points(points)
                points = []

        # Upload rimanenti
        if points:
            upload_points(points)

        print(f"   ✅ Aggiunti {len(chunks)} chunks da: {title}")
        return len(chunks)
    except Exception as e:
        print(f"   ❌ Errore aggiunta a Qdrant: {e}")
        return 0

def upload_points(points):
    """Carica punti in Qdrant"""
    try:
        response = requests.put(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points",
            json={"points": points},
            timeout=60
        )
        response.raise_for_status()
    except Exception as e:
        print(f"\n   ⚠️  Errore upload batch: {e}")

def process_urls_file(filename):
    """Processa file con URL (una per riga)"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        print(f"📋 Trovati {len(urls)} URL da processare\n")

        total_chunks = 0
        successful = 0
        failed = 0

        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processando: {url}")

            # Scarica contenuto
            text, title = fetch_url_content(url)
            if text is None:
                failed += 1
                continue

            print(f"   📄 Titolo: {title}")
            print(f"   📏 Lunghezza: {len(text)} caratteri")

            # Aggiungi a Qdrant (aspetta completamento prima di continuare)
            chunks_added = add_to_qdrant(url, text, title)
            if chunks_added > 0:
                successful += 1
                total_chunks += chunks_added
            else:
                failed += 1

            # Nessun delay - procede sequenzialmente dopo completamento

        # Riepilogo
        print(f"\n{'='*80}")
        print(f"✨ COMPLETATO!")
        print(f"   ✅ Successo: {successful}/{len(urls)} URL")
        print(f"   ❌ Falliti: {failed}/{len(urls)} URL")
        print(f"   📦 Totale chunks aggiunti: {total_chunks}")
        print(f"{'='*80}\n")

    except FileNotFoundError:
        print(f"❌ File non trovato: {filename}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Errore: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 add_urls_to_qdrant.py <file_urls.txt>")
        print("\nIl file deve contenere un URL per riga.")
        print("Esempio file_urls.txt:")
        print("  https://example.com/doc1")
        print("  https://example.com/doc2")
        print("  # Commento (righe con # sono ignorate)")
        sys.exit(1)

    urls_file = sys.argv[1]

    print("🚀 Script per aggiungere URL a Qdrant")
    print(f"📁 File URL: {urls_file}")
    print(f"🗄️  Collezione: {COLLECTION_NAME}")
    print(f"🤖 Modello embedding: nomic-embed-text via Ollama")
    print(f"✂️  Chunk size: {CHUNK_SIZE} caratteri (overlap: {CHUNK_OVERLAP})\n")

    # Verifica connessioni
    try:
        r = requests.get(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", timeout=5)
        r.raise_for_status()
        print("✅ Qdrant connesso")
    except:
        print("❌ Errore connessione a Qdrant")
        sys.exit(1)

    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        print("✅ Ollama connesso\n")
    except:
        print("❌ Errore connessione a Ollama")
        sys.exit(1)

    # Processa URLs
    process_urls_file(urls_file)

if __name__ == "__main__":
    main()
