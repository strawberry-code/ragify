# Piattaforma RAG - Ricerca Documentazione Self-Hosted

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> 🇬🇧 **English Version**: [README.md](README.md)

Una piattaforma RAG (Retrieval-Augmented Generation) completa per indicizzare e interrogare documentazione locale usando ricerca semantica con embeddings vettoriali.

## Avvio Rapido

### 1. Verifica Prerequisiti

```bash
python3 ragify.py doctor
```

Questo verifica:
- Python 3.10+ e dipendenze
- Java (per Apache Tika)
- Ollama con modello nomic-embed-text
- Database vettoriale Qdrant
- Spazio su disco

Usa `--fix` per auto-installare i pacchetti Python mancanti.

### 2. Indicizza la Documentazione

```bash
python3 ragify.py index ./docs
```

Ragify:
- Estrae testo da oltre 1000 formati di file (PDF, DOCX, MD, codice)
- Divide in chunks semantici
- Genera embeddings con Ollama
- Archivia in Qdrant per recupero veloce

### 3. Interroga i Documenti

```bash
python3 ragify.py query "come funziona l'autenticazione?"
```

**📖 Documentazione completa**: [docs/RAGIFY.md](docs/RAGIFY.md) | **⚡ Guida rapida**: [docs/QUICK_GUIDE.md](docs/QUICK_GUIDE.md)

---

## Cos'è Ragify?

**Ragify** è una pipeline automatizzata per indicizzare documentazione locale:

- ✅ **Nessun server HTTP** - Accesso diretto al filesystem
- ✅ **Formati universali** - PDF, DOCX, codice, markdown (via Apache Tika)
- ✅ **Deduplicazione intelligente** - Aggiornamenti incrementali basati su hash SHA-256
- ✅ **Chunking semantico** - Strategie specifiche per tipo di file
- ✅ **CLI tutto-in-uno** - Comandi index, query, list, reset

### Come Funziona

```
Documenti Locali
    ↓
[ragify index] → Estrai testo, chunking, embeddings
    ↓
[Ollama nomic-embed-text] → Genera vettori (768-dim)
    ↓
[Qdrant] → Archivia vettori + metadata
    ↓
[ragify query] → Ricerca semantica
```

---

## Installazione

### Prerequisiti

1. **Docker** - Per il database vettoriale Qdrant
2. **Ollama** - Per gli embeddings ([ollama.ai](https://ollama.ai/))
3. **Python 3.10+** - Con pip
4. **Java 8+** - Per Apache Tika (opzionale ma consigliato)

### Setup

```bash
# 1. Avvia Qdrant
docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# 2. Installa Ollama e scarica il modello
ollama pull nomic-embed-text

# 3. Installa le dipendenze Python
pip install -r requirements.txt

# 4. Verifica il sistema
python3 ragify.py doctor
```

---

## Integrazione MCP (Opzionale)

Interroga i documenti indicizzati da Claude Desktop o altri client MCP.

### Installa MCP Server

```bash
npm install -g @qpd-v/mcp-server-ragdocs
```

### Configura Claude Desktop

Aggiungi a `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ragdocs": {
      "command": "/path/to/node",
      "args": ["/path/to/mcp-server-ragdocs/build/index.js"],
      "env": {
        "QDRANT_URL": "http://127.0.0.1:6333",
        "QDRANT_COLLECTION": "documentation",
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

Trova i percorsi:
```bash
which node                    # Percorso Node
npm root -g                   # Percorso node_modules globale
```

**📖 Setup MCP dettagliato**: [docs/MCP_SETUP.md](docs/MCP_SETUP.md)

---

## Componenti

- **Ragify** - CLI per indicizzazione documenti (Python)
- **Qdrant** - Database vettoriale (Docker)
- **Ollama** - Embeddings locali (nomic-embed-text, 768-dim)
- **MCP Server** - Interfaccia query per client MCP (opzionale)

---

## Documentazione

- **[Documentazione Ragify](docs/RAGIFY.md)** - Guida completa
- **[Guida Rapida](docs/QUICK_GUIDE.md)** - Cheatsheet comandi
- **[Setup MCP](docs/MCP_SETUP.md)** - Integrazione Claude Desktop

---

## Variabili d'Ambiente

```bash
export OLLAMA_URL=http://localhost:11434
export QDRANT_URL=http://localhost:6333
export QDRANT_API_KEY=your-key  # Opzionale, per Qdrant Cloud
```

---

## Licenza

Licenza MIT - Vedi [LICENSE](LICENSE)

---

## Contribuire

Questo è un progetto personale. Sentiti libero di fare fork e adattarlo alle tue esigenze.
