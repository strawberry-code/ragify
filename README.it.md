# RAG Platform - Ricerca Documentazione Self-Hosted

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> 🇬🇧 **English Version**: [README.md](README.md)

Una piattaforma RAG (Retrieval-Augmented Generation) completa per indicizzare e cercare documentazione locale usando ricerca semantica con vector embeddings.

## Quick Start

### 1. Installa Dipendenze

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Verifica Prerequisiti

```bash
python3 ragify.py doctor
```

Questo verifica:
- Python 3.10+ e dipendenze
- Java (per Apache Tika)
- Ollama con modello nomic-embed-text
- Database vettoriale Qdrant
- Spazio disco

Usa `--fix` per installare automaticamente i pacchetti Python mancanti.

### 3. Indicizza la Documentazione

```bash
python3 ragify.py index ./docs         # → collection "docs"
```

Ragify:
- Estrae testo da 1000+ formati (PDF, DOCX, MD, file codice)
- Divide in chunk semantici
- Genera embeddings con Ollama
- Salva in Qdrant per ricerca veloce

**Collection multiple**: Il nome della cartella diventa automaticamente il nome della collection. Questo permette di organizzare i contenuti per argomento ed evitare bias nei risultati - una ricerca nella collection fisica non restituirà risultati di matematica:

```bash
python3 ragify.py index ./fisica       # → collection "fisica"
python3 ragify.py index ./matematica   # → collection "matematica"
python3 ragify.py index ./docs --collection custom  # → nome esplicito
```

### 4. Interroga i Documenti

```bash
python3 ragify.py query "come funziona l'autenticazione?"
python3 ragify.py query "calcolo integrale" --collection matematica
```

**📖 Documentazione completa**: [docs/RAGIFY.md](docs/RAGIFY.md) | **⚡ Guida rapida**: [docs/QUICK_GUIDE.md](docs/QUICK_GUIDE.md)

---

## Cos'è Ragify?

**Ragify** è una pipeline automatizzata per indicizzare documentazione locale:

- ✅ **Nessun server HTTP** - Accesso diretto al filesystem
- ✅ **Formati universali** - PDF, DOCX, codice, markdown (via Apache Tika)
- ✅ **Deduplicazione smart** - Aggiornamenti incrementali basati su hash SHA-256
- ✅ **Chunking semantico** - Strategie specifiche per tipo di file
- ✅ **CLI all-in-one** - Comandi index, query, list, reset

### Come Funziona

```
Documenti Locali
    ↓
[ragify index] → Estrai testo, chunk, embed
    ↓
[Ollama nomic-embed-text] → Genera vettori (768-dim)
    ↓
[Qdrant] → Salva vettori + metadati
    ↓
[ragify query] → Ricerca semantica
```

---

## Installazione

### Prerequisiti

1. **Docker + Qdrant** - Database vettoriale
   ```bash
   # Installa Docker: https://docs.docker.com/engine/install/
   docker run -d --name qdrant --restart unless-stopped \
     -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
   ```
2. **Ollama** - Per embeddings ([ollama.ai](https://ollama.ai/))
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull nomic-embed-text
   # Ollama gira come servizio systemd, parte automaticamente al boot
   sudo systemctl enable ollama && sudo systemctl start ollama
   ```
3. **Python 3.10+** - Con pip
4. **Java 21** - Per Apache Tika (opzionale ma consigliato)
   ```bash
   # Installa via sdkman (https://sdkman.io)
   sudo apt install zip unzip -y   # Ubuntu/Debian
   curl -s "https://get.sdkman.io" | bash
   source "$HOME/.sdkman/bin/sdkman-init.sh"
   sdk install java 21-zulu
   ```

### Setup

```bash
# 1. Avvia Qdrant
docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# 2. Installa Ollama e scarica il modello
ollama pull nomic-embed-text

# 3. Installa dipendenze Python
pip install -r requirements.txt

# 4. Verifica sistema
python3 ragify.py doctor
```

---

## Integrazione MCP (Opzionale)

Interroga i documenti indicizzati da Claude Desktop o Claude Code via MCP.

### Installazione

Nessuna installazione necessaria - usa [uvx](https://github.com/astral-sh/uv):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Configurazione

Aggiungi alla config MCP:
- **Claude Code**: `.mcp.json` nella root del progetto
- **Claude Desktop**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ragify": {
      "command": "uvx",
      "args": ["ragify-mcp"],
      "env": {
        "QDRANT_URL": "http://127.0.0.1:6333",
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

**📖 Setup MCP dettagliato**: [docs/MCP_SETUP.md](docs/MCP_SETUP.md)

### Perché Ollama + nomic-embed-text è Necessario

Claude è un modello di generazione testo - non può produrre vector embeddings. La ricerca semantica richiede la conversione delle query in vettori numerici.

**Architettura A: Singolo Ollama Remoto (consigliata)**
```
┌─────────────────────┐          ┌─────────────────────────────────────────┐
│    TUA MACCHINA     │          │            SERVER REMOTO                │
│                     │          │                                         │
│  Claude             │          │                                         │
│    │                │          │                                         │
│    ▼                │          │                                         │
│  ┌────────────┐     │  query   │  ┌─────────────────┐      ┌─────────┐   │
│  │ MCP Server │ ──────────────►│  │ Ollama + nomic  │ ───► │ Qdrant  │   │
│  └────────────┘     │          │  └─────────────────┘      └────┬────┘   │
│    ▲                │ risultati│                                │        │
│    └───────────────────────────────────────────────────────────-┘        │
│                     │          │         ▲                               │
│                     │          │         │ indexing                      │
│                     │          │    ragify index                         │
└─────────────────────┘          └─────────────────────────────────────────┘
```

**Architettura B: Ollama Locale per Query**
```
┌──────────────────────────┐          ┌─────────────────────────────┐
│      TUA MACCHINA        │          │       SERVER REMOTO         │
│                          │          │                             │
│  Claude                  │          │                             │
│    │                     │          │                             │
│    ▼                     │          │                             │
│  ┌────────────┐          │          │                             │
│  │ MCP Server │          │          │                             │
│  └─────┬──────┘          │          │                             │
│        │                 │          │                             │
│        ▼                 │          │                             │
│  ┌─────────────────┐     │  vettore │  ┌─────────┐                │
│  │ Ollama + nomic  │ ───────────────►  │ Qdrant  │                │
│  └─────────────────┘     │          │  └────┬────┘                │
│        ▲                 │ risultati│       │    ▲                │
│        └────────────────────────────────────┘    │                │
│                          │          │            │                │
│                          │          │  ┌─────────┴─────┐          │
│                          │          │  │ Ollama + nomic │          │
│                          │          │  └───────────────┘          │
│                          │          │            ▲                │
│                          │          │            │ indexing       │
│                          │          │       ragify index          │
│                          │          │                             │
└──────────────────────────┘          └─────────────────────────────┘
```

**Perché nomic-embed-text:** Embeddings allo stato dell'arte, solo ~274MB, ~50ms per query, 768 dimensioni.

Entrambe le architetture richiedono lo stesso modello `nomic-embed-text` per garantire la compatibilità dei vettori.

> **Sicurezza:** Se esponi Ollama remotamente, usa regole firewall, VPN, o reverse proxy con autenticazione.

**Architettura C: MCP Remoto via SSH (non consigliata)**

Questa configurazione esegue l'intero server MCP su una macchina remota, senza nulla in locale. Claude si connette via SSH stdio forwarding.

```
┌────────────────┐          ┌─────────────────────────────────────────┐
│  TUA MACCHINA  │          │            SERVER REMOTO                │
│                │          │                                         │
│  Claude        │   SSH    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│    │───────────────────────► │ MCP     │─►│ Ollama  │─►│ Qdrant  │  │
│    │◄──────────────────────  │ Server  │◄─┤ + nomic │◄─┤         │  │
│                │  stdio   │  └─────────┘  └─────────┘  └─────────┘  │
└────────────────┘          └─────────────────────────────────────────┘
```

⚠️ **Non consigliata** perché:
- Aggiunge latenza SSH a ogni richiesta MCP
- Richiede gestione chiavi SSH e connettività
- Debug più complesso in caso di problemi
- Le architetture A o B sono più semplici e affidabili

Se vuoi comunque questa configurazione, configura `.mcp.json`:

```json
{
  "mcpServers": {
    "ragify": {
      "command": "ssh",
      "args": [
        "-i", "~/.ssh/tua_chiave.pem",
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "utente@ip-server",
        "PATH=$HOME/.local/bin:$PATH QDRANT_URL=http://localhost:6333 OLLAMA_URL=http://localhost:11434 uvx ragify-mcp"
      ]
    }
  }
}
```

> **Nota:** `PATH=$HOME/.local/bin:$PATH` è necessario perché SSH non interattivo non carica `.bashrc`.

---

## Componenti

- **Ragify** - CLI per indicizzazione documenti (Python)
- **Qdrant** - Database vettoriale (Docker)
- **Ollama** - Embeddings locali (nomic-embed-text, 768-dim)
- **[ragify-mcp](https://pypi.org/project/ragify-mcp/)** - Server MCP per Claude Desktop/Code (opzionale)

---

## Documentazione

- **[Documentazione Ragify](docs/RAGIFY.md)** - Guida completa
- **[Riferimento Rapido](docs/QUICK_GUIDE.md)** - Cheatsheet comandi
- **[Setup MCP](docs/MCP_SETUP.md)** - Integrazione Claude Desktop

---

## Variabili d'Ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `QDRANT_URL` | http://localhost:6333 | URL server Qdrant |
| `QDRANT_API_KEY` | - | API key per autenticazione Qdrant (opzionale) |
| `OLLAMA_URL` | http://localhost:11434 | URL server Ollama |

```bash
# Esempio: connessione a Qdrant remoto con API key
export QDRANT_URL=http://tuo-server:6333
export QDRANT_API_KEY=tua-chiave-segreta
python3 ragify.py index ./docs
```

---

## Indicizzazioni Lunghe (SSH)

Usa tmux per mantenere l'indicizzazione attiva dopo la disconnessione SSH:

```bash
# Avvia sessione tmux
tmux new -s ragify

# Esegui indicizzazione
source .venv/bin/activate
python3 ragify.py index ./docs

# Stacca: Ctrl+B, poi D
# Riconnetti dopo: tmux attach -t ragify
```

---

## Licenza

MIT License - Vedi [LICENSE](LICENSE)

---

## Contribuire

Questo è un progetto personale. Sentiti libero di fare fork e adattarlo alle tue esigenze.
