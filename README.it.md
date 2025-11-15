# Piattaforma RAG - Documentazione Completa

> 🇬🇧 **English Version**: [README.md](README.md)

## Avvio Rapido

### Opzione 1: Installer Interattivo (Consigliato) 🚀

Esegui il bellissimo installer TUI costruito con [Charm](https://charm.sh):

```bash
cd installer
go build -o rag-installer
./rag-installer
```

L'installer:
- ✓ Controlla i requisiti di sistema
- ✓ Installa i componenti mancanti
- ✓ Configura tutto automaticamente
- ✓ Ti guida nella configurazione del client MCP

**[Vedi documentazione installer](installer/README.md)**

### Opzione 2: Installazione Manuale

Segui la sezione [Installazione da Zero](#installazione-da-zero) qui sotto.

---

## Indice
1. [Panoramica del Sistema](#panoramica-del-sistema)
2. [Componenti e Architettura](#componenti-e-architettura)
3. [Requisiti di Sistema](#requisiti-di-sistema)
4. [Installazione da Zero](#installazione-da-zero)
5. [Importazione Documentazione](#importazione-documentazione)
6. [Utilizzo e Query](#utilizzo-e-query)
7. [Manutenzione](#manutenzione)

---

## Panoramica del Sistema

Questa piattaforma RAG (Retrieval-Augmented Generation) consente di indicizzare documentazione locale e interrogarla tramite ricerca semantica usando embeddings vettoriali.

### Come Funziona

Il sistema converte documenti testuali in rappresentazioni vettoriali (embeddings) e li archivia in un database vettoriale. Quando effettui una query, il sistema:

1. **Converte la query** in un embedding vettoriale usando lo stesso modello
2. **Cerca i documenti più simili** nel database vettoriale usando similarità del coseno
3. **Restituisce i risultati più rilevanti** con score di rilevanza

### Flusso dei Dati

```
Documenti Locali
    ↓
[docs_server.py] → Serve file via HTTP
    ↓
[local_docs_url_generator.py] → Genera lista URL
    ↓
[add_urls_to_qdrant.py] → Scarica, chunka, genera embeddings
    ↓
[Ollama - nomic-embed-text] → Genera vettori (768 dimensioni)
    ↓
[Qdrant] → Archivia vettori + metadata
    ↓
[MCP Server ragdocs] → Interfaccia di query
    ↓
[Crush/Client] → Interroga la documentazione
```

---

## Componenti e Architettura

### 1. **Qdrant** - Database Vettoriale
- **Scopo**: Archiviazione e ricerca efficiente di vettori ad alta dimensione
- **Porta**: `6333`
- **Collection**: `documentation`
- **Dimensione vettori**: 768 (per nomic-embed-text)
- **Metrica di distanza**: Cosine similarity

### 2. **Ollama** - Modello di Embeddings
- **Modello**: `nomic-embed-text`
- **Dimensione output**: 768 dimensioni
- **Porta**: `11434`
- **API Endpoint**: `http://localhost:11434/api/embeddings`

### 3. **MCP Server ragdocs** - Interfaccia di Query
- **Package**: `@qpd-v/mcp-server-ragdocs`
- **Protocollo**: Model Context Protocol (MCP)
- **Comunicazione**: stdio
- **Funzioni**:
  - `search_documentation`: Ricerca semantica
  - `add_documentation`: Aggiungi documenti da URL
  - `list_sources`: Elenca sorgenti indicizzate
  - `test_ollama`: Testa configurazione embeddings

### 4. **docs_server.py** - Server HTTP per Documentazione Locale
- **Scopo**: Serve file locali via HTTP per permettere l'accesso da parte degli script di indicizzazione
- **Porta predefinita**: `8000`
- **Features**:
  - Directory listing HTML
  - CORS headers per crawler
  - Serve markdown, HTML, text files

### 5. **local_docs_url_generator.py** - Generatore URL
- **Scopo**: Scansiona directory locali e genera lista di URL da indicizzare
- **Filtri**: Esclude file nascosti, binari e immagini
- **Output**: File di testo con un URL per riga

### 6. **add_urls_to_qdrant.py** - Script di Indicizzazione
- **Scopo**: Scarica documenti, li chunka, genera embeddings e li carica su Qdrant
- **Chunking**: Divide testi in pezzi da ~1000 caratteri
- **Batch size**: 10 documenti alla volta
- **Metadata**:
  - `_type`: "DocumentChunk" (richiesto da MCP)
  - `text`: Contenuto del chunk
  - `url`: URL sorgente
  - `title`: Titolo del documento
  - `timestamp`: Data di indicizzazione
  - `chunk_index`: Indice del chunk
  - `total_chunks`: Totale chunks del documento

---

## Requisiti di Sistema

### Software Necessario

1. **Docker** (per Qdrant)
   - [Installazione Docker](https://docs.docker.com/get-docker/)

2. **Ollama**
   - [Installazione Ollama](https://ollama.ai/)

3. **Node.js** (per MCP server)
   - Versione 18 o superiore
   - [Installazione Node.js](https://nodejs.org/)

4. **Python 3**
   - Versione 3.8 o superiore
   - Librerie: `requests`, `beautifulsoup4`

5. **Crush CLI** (o altro client MCP compatibile)

### Requisiti Hardware Consigliati

- **RAM**: Minimo 8GB (consigliati 16GB per dataset grandi)
- **Spazio Disco**: Dipende dalla dimensione della documentazione (Qdrant usa ~1KB per vettore)
- **CPU**: Qualsiasi CPU moderna (embeddings gestiti da Ollama)

---

## Installazione da Zero

### Passo 1: Installa e Avvia Qdrant

```bash
# Scarica e avvia Qdrant via Docker
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Verifica che sia in esecuzione
curl http://localhost:6333/collections
```

**Output atteso**: Lista vuota di collezioni `{"result":{"collections":[]}}`

### Passo 2: Installa e Configura Ollama

```bash
# Installa Ollama (macOS/Linux)
# Segui le istruzioni su https://ollama.ai/

# Scarica il modello nomic-embed-text
ollama pull nomic-embed-text

# Verifica che funzioni
ollama list
```

**Output atteso**: Deve comparire `nomic-embed-text` tra i modelli

### Passo 3: Installa MCP Server ragdocs

```bash
# Installa via npm
npm install -g @qpd-v/mcp-server-ragdocs

# Verifica installazione
which mcp-server-ragdocs
```

### Passo 4: Configura Client MCP

Il MCP server ragdocs è compatibile con qualsiasi client che supporta il Model Context Protocol (MCP). La configurazione è identica per tutti i client.

#### Trova i Percorsi Necessari

Prima di configurare, trova i percorsi sul tuo sistema:

```bash
# Percorso Node.js
which node
# Esempio output: /Users/username/.nvm/versions/node/v22.3.0/bin/node

# Percorso MCP server
npm root -g
# Esempio output: /Users/username/.nvm/versions/node/v22.3.0/lib/node_modules
# Il path completo sarà: [output]/@qpd-v/mcp-server-ragdocs/build/index.js
```

#### Configurazione per Crush

**Requisito API Key**: Crush di [charm.land](https://charm.land) richiede una API Key di Anthropic. Anche se hai un piano subscription Claude Pro/Team, puoi ottenere una API Key con crediti gratuiti:

```bash
# Ottieni API Key Anthropic (anche con subscription)
bunx anthropic-api-key
```

Questo comando ti guiderà nella creazione di una API Key con crediti inclusi, utilizzabile con Crush.

Aggiungi la configurazione a `~/.config/crush/config.json`:

```json
{
  "mcp": {
    "ragdocs": {
      "type": "stdio",
      "command": "/Users/username/.nvm/versions/node/v22.3.0/bin/node",
      "args": ["/Users/username/.nvm/versions/node/v22.3.0/lib/node_modules/@qpd-v/mcp-server-ragdocs/build/index.js"],
      "timeout": 120,
      "disabled": false,
      "env": {
        "QDRANT_URL": "http://127.0.0.1:6333",
        "EMBEDDING_PROVIDER": "ollama",
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

**Nota**: Sostituisci `/Users/username/...` con i percorsi trovati sopra.

#### Configurazione per Claude Desktop

Aggiungi la stessa configurazione a `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) o `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "ragdocs": {
      "command": "/Users/username/.nvm/versions/node/v22.3.0/bin/node",
      "args": ["/Users/username/.nvm/versions/node/v22.3.0/lib/node_modules/@qpd-v/mcp-server-ragdocs/build/index.js"],
      "env": {
        "QDRANT_URL": "http://127.0.0.1:6333",
        "EMBEDDING_PROVIDER": "ollama",
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

#### Configurazione per Cline/Continue (VS Code)

Aggiungi la configurazione tramite l'interfaccia di Cline o modifica manualmente il file di configurazione MCP (solitamente `~/.cline/mcp_settings.json`):

```json
{
  "mcpServers": {
    "ragdocs": {
      "command": "/Users/username/.nvm/versions/node/v22.3.0/bin/node",
      "args": ["/Users/username/.nvm/versions/node/v22.3.0/lib/node_modules/@qpd-v/mcp-server-ragdocs/build/index.js"],
      "env": {
        "QDRANT_URL": "http://127.0.0.1:6333",
        "EMBEDDING_PROVIDER": "ollama",
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

**Riavvia il client** dopo aver modificato la configurazione.

### Passo 5: Installa Dipendenze Python

```bash
# Crea ambiente virtuale (opzionale ma consigliato)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Installa dipendenze
pip install requests beautifulsoup4
```

### Passo 6: Scarica gli Script di Supporto

Clona o copia questi file nella tua directory di lavoro:

- `docs_server.py` - Server HTTP per documentazione
- `local_docs_url_generator.py` - Generatore URL da filesystem
- `add_urls_to_qdrant.py` - Script di indicizzazione
- `reset_qdrant.py` - Reset collezione Qdrant

### Passo 7: Verifica l'Installazione

```bash
# 1. Verifica Qdrant
curl http://localhost:6333/collections

# 2. Verifica Ollama
curl http://localhost:11434/api/tags

# 3. Testa embedding
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "test"}'

# 4. Verifica MCP (tramite Crush)
# Apri Crush e prova: mcp_ragdocs_test_ollama con text="test"
```

---

## Importazione Documentazione

### Workflow Completo

#### Passo 1: Prepara la Documentazione

Organizza i tuoi file di documentazione in una directory:

```
/path/to/docs/
├── getting-started.md
├── api/
│   ├── overview.md
│   └── reference.md
└── guides/
    └── installation.md
```

#### Passo 2: Avvia il Server HTTP

```bash
# Avvia il server sulla directory della documentazione
python3 docs_server.py /path/to/docs --port 8000
```

**Output**:
```
Documentation Server
================================================================================
Serving directory: /path/to/docs
Server running at: http://localhost:8000
================================================================================
```

Lascia questo terminale aperto.

#### Passo 3: Genera Lista URL

In un **nuovo terminale**:

```bash
# Genera file con lista URL
python3 local_docs_url_generator.py /path/to/docs --output urls.txt
```

**Output**:
```
Scanning directory: /path/to/docs
--------------------------------------------------------------------------------
Found 125 files

================================================================================
Generated 125 URLs
================================================================================

URLs saved to: urls.txt
```

Il file `urls.txt` conterrà:
```
http://localhost:8000/getting-started.md
http://localhost:8000/api/overview.md
http://localhost:8000/api/reference.md
http://localhost:8000/guides/installation.md
```

**Nota**: Lo script esclude automaticamente:
- File nascosti (`.git`, `.DS_Store`)
- File binari compilati (`.pyc`, `.so`, `.exe`)
- Immagini (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.svg`, `.ico`, `.webp`)

#### Passo 4: Indicizza i Documenti

```bash
# Carica i documenti su Qdrant
python3 add_urls_to_qdrant.py urls.txt
```

**Output**:
```
📚 Caricamento documenti da: urls.txt
Trovati 125 URL da processare

[1/125] http://localhost:8000/getting-started.md
  ✓ Scaricato (2.4 KB)
  ✓ Estratto 3 chunks
  ✓ Caricato su Qdrant

[2/125] http://localhost:8000/api/overview.md
...

✨ Completato!
   - URL processati: 125
   - Chunks totali: 1,847
   - Tempo totale: 3m 42s
```

#### Passo 5: Verifica Indicizzazione

```bash
# Conta documenti in Qdrant
curl http://localhost:6333/collections/documentation | python3 -m json.tool
```

Oppure tramite Crush:
```
mcp_ragdocs_list_sources
```

### Aggiornamento Documentazione

Per aggiornare la documentazione:

1. **Aggiungi nuovi file** alla directory di documentazione
2. **Rigenera gli URL**:
   ```bash
   python3 local_docs_url_generator.py /path/to/docs --output new_urls.txt
   ```
3. **Indicizza solo i nuovi**:
   ```bash
   python3 add_urls_to_qdrant.py new_urls.txt
   ```

**Nota**: I documenti esistenti non vengono duplicati (stesso URL = aggiornamento)

### Reset Completo

Se vuoi ricominciare da zero:

```bash
# Elimina e ricrea la collezione
python3 reset_qdrant.py
```

Il script chiederà conferma:
```
⚠️  ATTENZIONE: Questa operazione eliminerà TUTTI i dati!
   Vuoi continuare? Scrivi 'RESET' per confermare:
```

---

## Utilizzo e Query

### Tramite Crush CLI

```bash
# Ricerca semantica
mcp_ragdocs_search_documentation query="come si creano i token" limit=5

# Elenca sorgenti
mcp_ragdocs_list_sources

# Testa configurazione
mcp_ragdocs_test_ollama text="test embedding"
```

### Tramite Script Python Diretto

Se vuoi testare senza MCP:

```bash
# Query diretta a Qdrant
python3 query_ragdocs.py "come si creano i token" --limit 5
```

**Output**:
```
[1] Score: 0.8276
Title: Token SDK Introduction
URL: http://localhost:8000/cordapps/token-sdk-introduction.md

Content:
The Tokens SDK provides you with the fastest and easiest way to create 
tokens that represent any kind of asset on your network...
```

---

## Manutenzione

### Monitoraggio

#### Verifica Stato Qdrant
```bash
# Info collezione
curl http://localhost:6333/collections/documentation

# Statistiche
curl http://localhost:6333/metrics
```

#### Verifica Spazio Disco
```bash
# Controlla dimensione storage Qdrant
du -sh qdrant_storage/
```

### Ottimizzazione

#### Indice Qdrant
Qdrant indicizza automaticamente, ma puoi forzare l'ottimizzazione:

```bash
curl -X POST http://localhost:6333/collections/documentation/optimizer
```

### Backup

#### Backup Qdrant
```bash
# Snapshot della collezione
curl -X POST http://localhost:6333/collections/documentation/snapshots/create

# La snapshot sarà salvata in qdrant_storage/snapshots/
```

#### Restore da Snapshot
```bash
curl -X PUT http://localhost:6333/collections/documentation/snapshots/upload \
  --data-binary @snapshot.dat
```

### Troubleshooting

#### Qdrant non raggiungibile
```bash
# Verifica container Docker
docker ps | grep qdrant

# Riavvia se necessario
docker restart qdrant
```

#### Ollama non risponde
```bash
# Verifica processo
ps aux | grep ollama

# Riavvia Ollama
ollama serve
```

#### Errori MCP "Invalid payload type"
Questo errore indica che i documenti in Qdrant non hanno i metadata richiesti.

**Soluzione**: Ricarica i documenti usando `add_urls_to_qdrant.py` aggiornato (versione corrente include tutti i campi necessari)

#### Risultati di ricerca poco rilevanti

1. **Verifica il modello di embedding**: Assicurati che Ollama stia usando `nomic-embed-text`
2. **Aumenta il limite di risultati**: Prova `limit=10` o `limit=20`
3. **Riduci la dimensione dei chunk**: Modifica `CHUNK_SIZE` in `add_urls_to_qdrant.py`

---

## File di Supporto

### Script Principali

| File | Scopo | Uso |
|------|-------|-----|
| `docs_server.py` | Server HTTP per documentazione locale | `python3 docs_server.py /path/to/docs` |
| `local_docs_url_generator.py` | Genera lista URL da filesystem | `python3 local_docs_url_generator.py /path/to/docs -o urls.txt` |
| `add_urls_to_qdrant.py` | Indicizza documenti su Qdrant | `python3 add_urls_to_qdrant.py urls.txt` |
| `reset_qdrant.py` | Reset collezione Qdrant | `python3 reset_qdrant.py` |

### Script di Test (opzionali)

| File | Scopo |
|------|-------|
| `query_ragdocs.py` | Test query dirette a Qdrant (bypass MCP) |
| `test_ragdocs.py` | Test completo del sistema |

### File di Migrazione (deprecati)

| File | Note |
|------|------|
| `migrate_qdrant_payloads.py` | Non più necessario - `add_urls_to_qdrant.py` ora genera i metadata corretti |

---

## Architettura dei Metadata

Ogni documento indicizzato ha la seguente struttura in Qdrant:

```json
{
  "id": "uuid-random",
  "vector": [0.123, 0.456, ...],  // 768 dimensioni
  "payload": {
    "_type": "DocumentChunk",
    "text": "Contenuto del chunk...",
    "url": "http://localhost:8000/path/to/file.md",
    "title": "Titolo del documento",
    "timestamp": "2025-11-14T12:00:00.000000",
    "chunk_index": 0,
    "total_chunks": 5
  }
}
```

**Campi obbligatori** (richiesti da MCP server):
- `_type`: Deve essere `"DocumentChunk"`
- `text`: Contenuto testuale
- `url`: URL sorgente
- `title`: Titolo
- `timestamp`: ISO 8601 timestamp

---

## Licenza e Crediti

- **Qdrant**: [Apache 2.0](https://github.com/qdrant/qdrant)
- **Ollama**: [MIT](https://github.com/ollama/ollama)
- **@qpd-v/mcp-server-ragdocs**: Verifica licenza del package

---

## Supporto e Contributi

Per problemi o suggerimenti, apri una issue nel repository del progetto.

**Versione documentazione**: 1.0  
**Ultimo aggiornamento**: Novembre 2025
