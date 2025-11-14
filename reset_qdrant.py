#!/usr/bin/env python3
"""
Script per resettare (eliminare e ricreare) una collezione Qdrant.
ATTENZIONE: Questo script eliminerà TUTTI i dati nella collezione!
"""

import requests
import sys

# Configurazione
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "documentation"
VECTOR_SIZE = 768  # Dimensione vettori per nomic-embed-text

def collection_exists(collection_name):
    """Verifica se la collezione esiste"""
    try:
        response = requests.get(f"{QDRANT_URL}/collections/{collection_name}")
        return response.status_code == 200
    except:
        return False

def get_collection_info(collection_name):
    """Ottiene info sulla collezione"""
    try:
        response = requests.get(f"{QDRANT_URL}/collections/{collection_name}")
        if response.status_code == 200:
            return response.json()["result"]
        return None
    except:
        return None

def delete_collection(collection_name):
    """Elimina la collezione"""
    try:
        print(f"🗑️  Eliminando collezione '{collection_name}'...")
        response = requests.delete(f"{QDRANT_URL}/collections/{collection_name}")
        response.raise_for_status()
        print(f"✅ Collezione '{collection_name}' eliminata")
        return True
    except Exception as e:
        print(f"❌ Errore eliminazione: {e}")
        return False

def create_collection(collection_name, vector_size):
    """Crea una nuova collezione"""
    try:
        print(f"🔨 Creando collezione '{collection_name}'...")
        response = requests.put(
            f"{QDRANT_URL}/collections/{collection_name}",
            json={
                "vectors": {
                    "size": vector_size,
                    "distance": "Cosine"
                }
            }
        )
        response.raise_for_status()
        print(f"✅ Collezione '{collection_name}' creata")
        print(f"   📏 Dimensione vettori: {vector_size}")
        print(f"   📐 Distanza: Cosine")
        return True
    except Exception as e:
        print(f"❌ Errore creazione: {e}")
        return False

def reset_collection(collection_name, vector_size):
    """Reset completo: elimina e ricrea la collezione"""
    print(f"\n{'='*80}")
    print(f"🔄 RESET COLLEZIONE QDRANT")
    print(f"{'='*80}\n")

    # Verifica connessione
    try:
        response = requests.get(f"{QDRANT_URL}/collections")
        response.raise_for_status()
        print("✅ Qdrant connesso\n")
    except:
        print("❌ Errore: Impossibile connettersi a Qdrant")
        print(f"   Verifica che Qdrant sia in esecuzione su {QDRANT_URL}")
        sys.exit(1)

    # Mostra info collezione esistente
    if collection_exists(collection_name):
        info = get_collection_info(collection_name)
        if info:
            points_count = info.get("points_count", 0)
            vectors_count = info.get("indexed_vectors_count", 0)
            print(f"📊 Collezione esistente '{collection_name}':")
            print(f"   📦 Punti totali: {points_count}")
            print(f"   🔢 Vettori indicizzati: {vectors_count}\n")

        # Conferma
        print("⚠️  ATTENZIONE: Questa operazione eliminerà TUTTI i dati!")
        confirm = input(f"   Vuoi continuare? Scrivi 'RESET' per confermare: ")

        if confirm != "RESET":
            print("\n❌ Operazione annullata")
            sys.exit(0)

        print()

        # Elimina
        if not delete_collection(collection_name):
            sys.exit(1)
    else:
        print(f"ℹ️  Collezione '{collection_name}' non esiste\n")

    # Ricrea
    if not create_collection(collection_name, vector_size):
        sys.exit(1)

    # Verifica
    print(f"\n🔍 Verificando collezione...")
    info = get_collection_info(collection_name)
    if info:
        print(f"✅ Collezione '{collection_name}' pronta all'uso")
        print(f"   📦 Punti: {info.get('points_count', 0)}")
        print(f"   📏 Dimensione vettori: {info['config']['params']['vectors']['size']}")

    print(f"\n{'='*80}")
    print("✨ RESET COMPLETATO!")
    print(f"{'='*80}\n")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print("Uso: python3 reset_qdrant.py [collection_name] [vector_size]")
            print("\nParametri opzionali:")
            print(f"  collection_name  Nome collezione (default: {COLLECTION_NAME})")
            print(f"  vector_size      Dimensione vettori (default: {VECTOR_SIZE})")
            print("\nEsempi:")
            print("  python3 reset_qdrant.py")
            print("  python3 reset_qdrant.py my_collection 768")
            print("\nNote:")
            print("  - Vector size 768 = nomic-embed-text, all-mpnet-base-v2")
            print("  - Vector size 384 = all-MiniLM-L6-v2")
            sys.exit(0)

        collection = sys.argv[1] if len(sys.argv) > 1 else COLLECTION_NAME
        vector_size = int(sys.argv[2]) if len(sys.argv) > 2 else VECTOR_SIZE
    else:
        collection = COLLECTION_NAME
        vector_size = VECTOR_SIZE

    reset_collection(collection, vector_size)

if __name__ == "__main__":
    main()
