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
3. [Ragify - Indicizzazione Documenti Moderna](#ragify---indicizzazione-documenti-moderna)
4. [Requisiti di Sistema](#requisiti-di-sistema)
5. [Installazione da Zero](#installazione-da-zero)
6. [Importazione Documentazione](#importazione-documentazione)
7. [Utilizzo e Query](#utilizzo-e-query)
8. [Manutenzione](#manutenzione)

---

## Panoramica del Sistema

Questa piattaforma RAG (Retrieval-Augmented Generation) consente di indicizzare documentazione locale e interrogarla tramite ricerca semantica usando embeddings vettoriali.

### Come Funziona

Il sistema converte documenti testuali in rappresentazioni vettoriali (embeddings) e li archivia in un database vettoriale. Quando effettui una query, il sistema:

1. **Converte la query** in un embedding vettoriale usando lo stesso modello
2. **Cerca i documenti più simili** nel database vettoriale usando similarità del coseno
3. **Restituisce i risultati più rilevanti** con score di rilevanza

### Flusso dei Dati

**Approccio Moderno (Ragify):**
```
Documenti Locali
    ↓
[ragify index] → Accesso diretto ai file, chunking, generazione embeddings
    ↓
[Ollama - nomic-embed-text] → Genera vettori (768 dimensioni)
    ↓
[Qdrant] → Archivia vettori + metadata
    ↓
[ragify query] → Ricerca semantica
```

**Approccio Legacy (basato su URL):**
```
Documenti Locali → [docs_server.py] → [local_docs_url_generator.py]
    → [add_urls_to_qdrant.py] → [Qdrant]
```

---

## Ragify - Indicizzazione Documenti Moderna

**Ragify** è l'approccio moderno e semplificato per indicizzare documentazione. Sostituisce il workflow a tre passi con server HTTP con accesso diretto al filesystem.

### Perché Ragify?

- ✅ **Nessun server HTTP necessario** - Accesso diretto ai file
- ✅ **Supporto universale formati** - PDF, DOCX, codice, markdown (oltre 1000 formati via Apache Tika)
- ✅ **Deduplicazione intelligente** - Aggiornamenti incrementali basati su hash SHA-256
- ✅ **Chunking specifico per tipo** - Strategie ottimizzate per ogni tipo di file
- ✅ **Tutto-in-uno** - Indicizza, interroga, elenca e resetta in un unico CLI

### Avvio Rapido con Ragify

```bash
# Indicizza una directory
python3 ragify.py index ./docs

# Interroga i documenti indicizzati
python3 ragify.py query "autenticazione"

# Elenca tutti i file indicizzati
python3 ragify.py list
```

**📖 Documentazione completa**: [docs/RAGIFY.md](docs/RAGIFY.md) | **⚡ Guida rapida**: [docs/QUICK_GUIDE.md](docs/QUICK_GUIDE.md)

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
- **Scopo**: Scarica documenti, li chunka usando analisi semantica, genera embeddings e li carica su Qdrant
- **Strategia di Chunking**: Chunking semantico a due livelli
  - **Livello 1 (Chonkie)**: Macro-blocchi semantici (~512 token) che rispettano la struttura del documento
  - **Livello 2 (semchunk)**: Chunks granulari (400-600 token) ottimizzati per embeddings
  - **Token-based**: Usa tiktoken per conteggio token accurato
  - **Re-chunking automatico**: Chunks troppo grandi divisi automaticamente per rispettare limiti del modello (8192 token)
- **Meccanismi di fallback**: Se le librerie semantiche non sono disponibili, degrada gradualmente a chunking basato su caratteri
- **Opzioni CLI**:
  - `--chunk-size`: Dimensione target chunk in token (default: 512)
  - `--overlap`: Sovrapposizione tra chunks in token (default: 51)
  - `--verbose`: Logging dettagliato
- **Metadata**:
  - `_type`: "DocumentChunk" (richiesto da MCP)
  - `text`: Contenuto del chunk
  - `url`: URL sorgente
  - `title`: Titolo del documento
  - `timestamp`: Data di indicizzazione
  - `chunk_index`: Indice del chunk
  - `total_chunks`: Totale chunks del documento
  - `semantic_block_index`: Macro-blocco dal chunking di Livello 1
  - `token_count`: Conteggio token effettivo
  - `chunking_method`: Metodo usato ('semantic', 'fallback', etc.)
  - `embedding_model`: Modello usato per gli embeddings

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
   - Versione 3.10 o superiore (richiesto per chunking semantico)
   - Librerie: vedi `requirements.txt`

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
# Verifica versione Python (richiesto 3.10+)
python3 --version

# Crea ambiente virtuale (opzionale ma consigliato)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Installa dipendenze
pip install -r requirements.txt
```

**Pacchetti richiesti** (da `requirements.txt`):
- `requests` - Richieste HTTP
- `beautifulsoup4` - Parsing HTML
- `qdrant-client` - Client database vettoriale Qdrant
- `chonkie>=0.1.0` - Macro-chunking semantico
- `semchunk>=2.0.0` - Chunking semantico granulare
- `tiktoken>=0.5.0` - Conteggio token per modelli OpenAI

### Passo 6: Scarica gli Script di Supporto

Clona questo repository o copia questi file nella tua directory di lavoro:

**Script principali:**
- `docs_server.py` - Server HTTP per documentazione
- `local_docs_url_generator.py` - Generatore URL da filesystem
- `add_urls_to_qdrant.py` - Script di indicizzazione con chunking semantico
- `reset_qdrant.py` - Reset collezione Qdrant

**Moduli libreria** (package `lib/`):
- `lib/text_cleaning.py` - Normalizzazione testo e validazione qualità
- `lib/chunking.py` - Motore di chunking semantico a due livelli
- `lib/embedding.py` - Generazione embeddings con re-chunking automatico
- `lib/qdrant_operations.py` - Operazioni database Qdrant

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
# Carica i documenti su Qdrant con chunking semantico (consigliato)
python3 add_urls_to_qdrant.py urls.txt

# Uso avanzato con parametri personalizzati
python3 add_urls_to_qdrant.py urls.txt --chunk-size 600 --overlap 60 --verbose
```

**Opzioni CLI**:
- `--chunk-size SIZE`: Dimensione target chunk in token (default: 512)
- `--overlap SIZE`: Sovrapposizione tra chunks in token (default: 51, ~10%)
- `--verbose`: Mostra informazioni di elaborazione dettagliate

**Output**:
```
📚 Avvio pipeline di indicizzazione documenti
================================================================================
File input: urls.txt
Dimensione chunk: 512 token | Sovrapposizione: 51 token
================================================================================

[1/125] Elaborazione: http://localhost:8000/getting-started.md
  ✓ Scaricato (2.431 caratteri)
  ✓ Pulito (2.387 caratteri dopo normalizzazione)
  ✓ Chunking semantico: 1 macro-blocco → 3 chunks finali
  ✓ Statistiche token: avg=445, min=412, max=487 token
  ✓ Embeddings generati e caricati

[2/125] Elaborazione: http://localhost:8000/api/overview.md
...

================================================================================
📊 Statistiche Indicizzazione
================================================================================
URL elaborati:      125 / 125 (100.0%)
Caratteri totali:   1.245.890 (grezzo) → 1.238.122 (pulito)
Macro-blocchi:      387 blocchi semantici
Chunks finali:      1.847 chunks pronti per embedding
Distribuzione token: avg=478, min=402, max=598 token
Tasso successo:     98.4% (123 successi, 2 falliti)
Tempo totale:       4m 18s
================================================================================
```

**Cosa succede durante l'indicizzazione**:
1. **Download**: Scarica il contenuto HTML da ogni URL
2. **Estrazione testo**: Estrae il testo usando BeautifulSoup
3. **Pulizia**: Normalizzazione Unicode, pulizia whitespace, rimozione boilerplate
4. **Validazione qualità**: Verifica lunghezza minima e diversità caratteri
5. **Chunking semantico (Livello 1)**: Chonkie crea macro-blocchi rispettando la struttura del documento
6. **Chunking fine (Livello 2)**: semchunk divide i blocchi in dimensioni ottimali per embedding
7. **Validazione token**: Assicura che tutti i chunks rispettino i limiti del modello (8192 token)
8. **Generazione embeddings**: Crea vettori usando Ollama nomic-embed-text
9. **Upload**: Archivia vettori + metadata in Qdrant

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
3. **Regola la dimensione dei chunk**: Re-indicizza con un parametro `--chunk-size` diverso
   ```bash
   python3 add_urls_to_qdrant.py urls.txt --chunk-size 400  # Chunks più piccoli
   python3 add_urls_to_qdrant.py urls.txt --chunk-size 600  # Chunks più grandi
   ```
4. **Verifica metodo di chunking**: Controlla i log per assicurarti che il chunking semantico funzioni (non stia usando il fallback basato su caratteri)

#### Chunking semantico non funziona

Se vedi "Chonkie not available, using fallback" nei log:

1. **Verifica versione Python**: Deve essere 3.10 o superiore
   ```bash
   python3 --version
   ```
2. **Reinstalla le dipendenze**:
   ```bash
   pip install --upgrade chonkie semchunk tiktoken
   ```
3. **Controlla errori di import**:
   ```bash
   python3 -c "import chonkie; import semchunk; import tiktoken; print('Tutto OK')"
   ```

---

## File di Supporto

### Script Principali

| File | Scopo | Uso |
|------|-------|-----|
| `docs_server.py` | Server HTTP per documentazione locale | `python3 docs_server.py /path/to/docs` |
| `local_docs_url_generator.py` | Genera lista URL da filesystem | `python3 local_docs_url_generator.py /path/to/docs -o urls.txt` |
| `add_urls_to_qdrant.py` | Indicizza documenti con chunking semantico | `python3 add_urls_to_qdrant.py urls.txt [--chunk-size SIZE] [--overlap SIZE] [--verbose]` |
| `reset_qdrant.py` | Reset collezione Qdrant | `python3 reset_qdrant.py` |

### Moduli Libreria (package `lib/`)

| File | Scopo | Funzioni Chiave |
|------|-------|-----------------|
| `lib/text_cleaning.py` | Normalizzazione testo e validazione qualità | `clean_text()`, `remove_boilerplate()`, `validate_text_quality()` |
| `lib/chunking.py` | Chunking semantico a due livelli | `semantic_chunk_text()`, `fine_chunk_text()`, `count_tokens()`, `validate_chunk_size()` |
| `lib/embedding.py` | Generazione embeddings con validazione | `get_embedding()`, `safe_embed_chunk()`, `batch_embed_chunks()` |
| `lib/qdrant_operations.py` | Operazioni database Qdrant | `create_point()`, `upload_points()`, `batch_upload_chunks()` |

### Script di Test (opzionali)

| File | Scopo |
|------|-------|
| `query_ragdocs.py` | Test query dirette a Qdrant (bypass MCP) |
| `test_ragdocs.py` | Test completo del sistema |

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
    "total_chunks": 5,
    "semantic_block_index": 0,
    "token_count": 478,
    "chunking_method": "semantic",
    "embedding_model": "nomic-embed-text"
  }
}
```

**Campi obbligatori** (richiesti da MCP server):
- `_type`: Deve essere `"DocumentChunk"`
- `text`: Contenuto testuale
- `url`: URL sorgente
- `title`: Titolo
- `timestamp`: ISO 8601 timestamp

**Campi aggiuntivi** (metadata chunking semantico):
- `semantic_block_index`: Indice del macro-blocco dal chunking di Livello 1
- `token_count`: Conteggio token effettivo per questo chunk
- `chunking_method`: Strategia di chunking usata (`"semantic"`, `"fallback"`, etc.)
- `embedding_model`: Modello usato per generare gli embeddings

---

## Licenza e Crediti

- **Qdrant**: [Apache 2.0](https://github.com/qdrant/qdrant)
- **Ollama**: [MIT](https://github.com/ollama/ollama)
- **@qpd-v/mcp-server-ragdocs**: Verifica licenza del package

---

## Supporto e Contributi

Per problemi o suggerimenti, apri una issue nel repository del progetto.

---

## Funzionalità Avanzate

### Architettura Chunking Semantico

La piattaforma usa un sofisticato approccio di chunking semantico a due livelli:

#### Livello 1: Chunking Macro (Chonkie)
- **Scopo**: Dividere documenti in macro-blocchi semanticamente coerenti
- **Strategia**: Rispetta la struttura del documento (paragrafi, sezioni, interruzioni logiche)
- **Dimensione target**: ~512 token per blocco
- **Beneficio**: Preserva il contesto semantico di alto livello

#### Livello 2: Chunking Granulare (semchunk)
- **Scopo**: Dividere i macro-blocchi in chunks ottimali per embedding
- **Strategia**: Divisione basata su token con consapevolezza dei confini semantici
- **Dimensione target**: 400-600 token per chunk
- **Beneficio**: Ottimale per embeddings vettoriali mantenendo coerenza semantica

#### Token-based vs Caratteri

**Perché chunking basato su token?**
- I modelli di embedding hanno limiti di token (nomic-embed-text: 8192 token)
- Previene errori di overflow del modello
- Rappresentazione più accurata dell'input del modello
- Migliore consistenza semantica tra i chunks

**Validazione e re-chunking automatico:**
- Tutti i chunks validati contro i limiti token del modello
- Chunks troppo grandi automaticamente divisi al 50% della dimensione massima
- Conteggio token usando `tiktoken` (tokenizer di OpenAI)

#### Meccanismi di Fallback

Il sistema degrada gradualmente se le librerie semantiche non sono disponibili:
1. **Chonkie non disponibile** → Tratta l'intero documento come singolo macro-blocco
2. **Semchunk non disponibile** → Fallback a finestra scorrevole basata su caratteri
3. **Entrambi non disponibili** → Chunking semplice basato su caratteri (~1000 caratteri)

I log indicano quale metodo è attivo per trasparenza.

### Ottimizzazione Prestazioni

#### Ottimizzazione Dimensione Chunk

**Chunks più piccoli (300-400 token)**:
- ✅ Risultati più precisi
- ✅ Migliori per query specifiche
- ❌ Più chunks = database più grande
- ❌ Indicizzazione più lenta

**Chunks più grandi (500-600 token)**:
- ✅ Più contesto per risultato
- ✅ Meno chunks = database più piccolo
- ✅ Indicizzazione più veloce
- ❌ Matching meno preciso

**Punto di partenza consigliato**: 512 token (bilanciato)

#### Configurazione Sovrapposizione

**Scopo**: Previene che informazioni importanti vengano divise tra confini di chunk

**Valori consigliati**:
- Minimo: 5% (`--overlap 25` per chunks di 512 token)
- Default: 10% (`--overlap 51` per chunks di 512 token)
- Massimo: 20% (`--overlap 102` per chunks di 512 token)

Maggiore sovrapposizione = migliore gestione confini ma più storage.

---

**Versione documentazione**: 2.0 (con chunking semantico)  
**Ultimo aggiornamento**: Novembre 2025
