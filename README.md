# RAG Platform - Complete Documentation

> 🇮🇹 **Versione Italiana**: [README.it.md](README.it.md)

## Quick Start

### Option 1: Interactive Installer (Recommended) 🚀

Run the beautiful TUI installer built with [Charm](https://charm.sh):

```bash
cd installer
go build -o rag-installer
./rag-installer
```

The installer will:
- ✓ Check system requirements
- ✓ Install missing components
- ✓ Configure everything automatically
- ✓ Guide you through MCP client setup

**[See installer documentation](installer/README.md)**

### Option 2: Manual Installation

Follow the [Installation from Scratch](#installation-from-scratch) section below.

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Components and Architecture](#components-and-architecture)
3. [System Requirements](#system-requirements)
4. [Installation from Scratch](#installation-from-scratch)
5. [Importing Documentation](#importing-documentation)
6. [Usage and Queries](#usage-and-queries)
7. [Maintenance](#maintenance)

---

## System Overview

This RAG (Retrieval-Augmented Generation) platform allows you to index local documentation and query it using semantic search with vector embeddings.

### How It Works

The system converts text documents into vector representations (embeddings) and stores them in a vector database. When you perform a query, the system:

1. **Converts the query** into a vector embedding using the same model
2. **Searches for the most similar documents** in the vector database using cosine similarity
3. **Returns the most relevant results** with relevance scores

### Data Flow

```
Local Documents
    ↓
[docs_server.py] → Serves files via HTTP
    ↓
[local_docs_url_generator.py] → Generates URL list
    ↓
[add_urls_to_qdrant.py] → Downloads, chunks, generates embeddings
    ↓
[Ollama - nomic-embed-text] → Generates vectors (768 dimensions)
    ↓
[Qdrant] → Stores vectors + metadata
    ↓
[MCP Server ragdocs] → Query interface
    ↓
[Crush/Client] → Query the documentation
```

---

## Components and Architecture

### 1. **Qdrant** - Vector Database
- **Purpose**: Efficient storage and search of high-dimensional vectors
- **Port**: `6333`
- **Collection**: `documentation`
- **Vector dimension**: 768 (for nomic-embed-text)
- **Distance metric**: Cosine similarity

### 2. **Ollama** - Embeddings Model
- **Model**: `nomic-embed-text`
- **Output dimension**: 768 dimensions
- **Port**: `11434`
- **API Endpoint**: `http://localhost:11434/api/embeddings`

### 3. **MCP Server ragdocs** - Query Interface
- **Package**: `@qpd-v/mcp-server-ragdocs`
- **Protocol**: Model Context Protocol (MCP)
- **Communication**: stdio
- **Functions**:
  - `search_documentation`: Semantic search
  - `add_documentation`: Add documents from URL
  - `list_sources`: List indexed sources
  - `test_ollama`: Test embeddings configuration

### 4. **docs_server.py** - HTTP Server for Local Documentation
- **Purpose**: Serves local files via HTTP to allow access by indexing scripts
- **Default port**: `8000`
- **Features**:
  - HTML directory listing
  - CORS headers for crawler
  - Serves markdown, HTML, text files

### 5. **local_docs_url_generator.py** - URL Generator
- **Purpose**: Scans local directories and generates list of URLs to index
- **Filters**: Excludes hidden files, binaries, and images
- **Output**: Text file with one URL per line

### 6. **add_urls_to_qdrant.py** - Indexing Script
- **Purpose**: Downloads documents, chunks them, generates embeddings and loads them to Qdrant
- **Chunking**: Splits texts into ~1000 character pieces
- **Batch size**: 10 documents at a time
- **Metadata**:
  - `_type`: "DocumentChunk" (required by MCP)
  - `text`: Chunk content
  - `url`: Source URL
  - `title`: Document title
  - `timestamp`: Indexing date
  - `chunk_index`: Chunk index
  - `total_chunks`: Total chunks in document

---

## System Requirements

### Required Software

1. **Docker** (for Qdrant)
   - [Docker Installation](https://docs.docker.com/get-docker/)

2. **Ollama**
   - [Ollama Installation](https://ollama.ai/)

3. **Node.js** (for MCP server)
   - Version 18 or higher
   - [Node.js Installation](https://nodejs.org/)

4. **Python 3**
   - Version 3.8 or higher
   - Libraries: `requests`, `beautifulsoup4`

5. **Crush CLI** (or other MCP-compatible client)

### Recommended Hardware

- **RAM**: Minimum 8GB (16GB recommended for large datasets)
- **Disk Space**: Depends on documentation size (Qdrant uses ~1KB per vector)
- **CPU**: Any modern CPU (embeddings handled by Ollama)

---

## Installation from Scratch

### Step 1: Install and Start Qdrant

```bash
# Download and start Qdrant via Docker
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Verify it's running
curl http://localhost:6333/collections
```

**Expected output**: Empty collections list `{"result":{"collections":[]}}`

### Step 2: Install and Configure Ollama

```bash
# Install Ollama (macOS/Linux)
# Follow instructions at https://ollama.ai/

# Download the nomic-embed-text model
ollama pull nomic-embed-text

# Verify it works
ollama list
```

**Expected output**: `nomic-embed-text` should appear in the models list

### Step 3: Install MCP Server ragdocs

```bash
# Install via npm
npm install -g @qpd-v/mcp-server-ragdocs

# Verify installation
which mcp-server-ragdocs
```

### Step 4: Configure MCP Client

The MCP server ragdocs is compatible with any client that supports the Model Context Protocol (MCP). Configuration is identical for all clients.

#### Find Required Paths

Before configuring, find the paths on your system:

```bash
# Node.js path
which node
# Example output: /Users/username/.nvm/versions/node/v22.3.0/bin/node

# MCP server path
npm root -g
# Example output: /Users/username/.nvm/versions/node/v22.3.0/lib/node_modules
# Full path will be: [output]/@qpd-v/mcp-server-ragdocs/build/index.js
```

#### Configuration for Crush

**API Key Requirement**: Crush from [charm.land](https://charm.land) requires an Anthropic API Key. Even if you have a Claude Pro/Team subscription, you can get an API Key with free credits:

```bash
# Get Anthropic API Key (even with subscription)
bunx anthropic-api-key
```

This command will guide you through creating an API Key with included credits, usable with Crush.

Add the configuration to `~/.config/crush/config.json`:

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

**Note**: Replace `/Users/username/...` with the paths found above.

#### Configuration for Claude Desktop

Add the same configuration to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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

#### Configuration for Cline/Continue (VS Code)

Add the configuration via the Cline interface or manually edit the MCP configuration file (usually `~/.cline/mcp_settings.json`):

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

**Restart the client** after modifying the configuration.

### Step 5: Install Python Dependencies

```bash
# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 6: Download Support Scripts

Clone or copy these files to your working directory:

- `docs_server.py` - HTTP server for documentation
- `local_docs_url_generator.py` - URL generator from filesystem
- `add_urls_to_qdrant.py` - Indexing script
- `reset_qdrant.py` - Reset Qdrant collection

### Step 7: Verify Installation

```bash
# 1. Verify Qdrant
curl http://localhost:6333/collections

# 2. Verify Ollama
curl http://localhost:11434/api/tags

# 3. Test embedding
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "test"}'

# 4. Verify MCP (via Crush)
# Open Crush and try: mcp_ragdocs_test_ollama with text="test"
```

---

## Importing Documentation

### Complete Workflow

#### Step 1: Prepare Documentation

Organize your documentation files in a directory:

```
/path/to/docs/
├── getting-started.md
├── api/
│   ├── overview.md
│   └── reference.md
└── guides/
    └── installation.md
```

#### Step 2: Start HTTP Server

```bash
# Start server on documentation directory
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

Leave this terminal open.

#### Step 3: Generate URL List

In a **new terminal**:

```bash
# Generate file with URL list
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

The `urls.txt` file will contain:
```
http://localhost:8000/getting-started.md
http://localhost:8000/api/overview.md
http://localhost:8000/api/reference.md
http://localhost:8000/guides/installation.md
```

**Note**: The script automatically excludes:
- Hidden files (`.git`, `.DS_Store`)
- Compiled binary files (`.pyc`, `.so`, `.exe`)
- Images (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.svg`, `.ico`, `.webp`)

#### Step 4: Index Documents

```bash
# Load documents to Qdrant
python3 add_urls_to_qdrant.py urls.txt
```

**Output**:
```
📚 Loading documents from: urls.txt
Found 125 URLs to process

[1/125] http://localhost:8000/getting-started.md
  ✓ Downloaded (2.4 KB)
  ✓ Extracted 3 chunks
  ✓ Loaded to Qdrant

[2/125] http://localhost:8000/api/overview.md
...

✨ Complete!
   - URLs processed: 125
   - Total chunks: 1,847
   - Total time: 3m 42s
```

#### Step 5: Verify Indexing

```bash
# Count documents in Qdrant
curl http://localhost:6333/collections/documentation | python3 -m json.tool
```

Or via Crush:
```
mcp_ragdocs_list_sources
```

### Updating Documentation

To update documentation:

1. **Add new files** to documentation directory
2. **Regenerate URLs**:
   ```bash
   python3 local_docs_url_generator.py /path/to/docs --output new_urls.txt
   ```
3. **Index only new ones**:
   ```bash
   python3 add_urls_to_qdrant.py new_urls.txt
   ```

**Note**: Existing documents are not duplicated (same URL = update)

### Complete Reset

To start from scratch:

```bash
# Delete and recreate collection
python3 reset_qdrant.py
```

The script will ask for confirmation:
```
⚠️  WARNING: This operation will delete ALL data!
   Do you want to continue? Type 'RESET' to confirm:
```

---

## Usage and Queries

### Via Crush CLI

```bash
# Semantic search
mcp_ragdocs_search_documentation query="how to create tokens" limit=5

# List sources
mcp_ragdocs_list_sources

# Test configuration
mcp_ragdocs_test_ollama text="test embedding"
```

### Via Direct Python Script

To test without MCP:

```bash
# Direct query to Qdrant
python3 query_ragdocs.py "how to create tokens" --limit 5
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

## Maintenance

### Monitoring

#### Check Qdrant Status
```bash
# Collection info
curl http://localhost:6333/collections/documentation

# Statistics
curl http://localhost:6333/metrics
```

#### Check Disk Space
```bash
# Check Qdrant storage size
du -sh qdrant_storage/
```

### Optimization

#### Qdrant Index
Qdrant indexes automatically, but you can force optimization:

```bash
curl -X POST http://localhost:6333/collections/documentation/optimizer
```

### Backup

#### Backup Qdrant
```bash
# Collection snapshot
curl -X POST http://localhost:6333/collections/documentation/snapshots/create

# Snapshot will be saved in qdrant_storage/snapshots/
```

#### Restore from Snapshot
```bash
curl -X PUT http://localhost:6333/collections/documentation/snapshots/upload \
  --data-binary @snapshot.dat
```

### Troubleshooting

#### Qdrant not reachable
```bash
# Verify Docker container
docker ps | grep qdrant

# Restart if needed
docker restart qdrant
```

#### Ollama not responding
```bash
# Verify process
ps aux | grep ollama

# Restart Ollama
ollama serve
```

#### MCP errors "Invalid payload type"
This error indicates that documents in Qdrant don't have the required metadata.

**Solution**: Reload documents using updated `add_urls_to_qdrant.py` (current version includes all necessary fields)

#### Irrelevant search results

1. **Verify embedding model**: Make sure Ollama is using `nomic-embed-text`
2. **Increase result limit**: Try `limit=10` or `limit=20`
3. **Reduce chunk size**: Modify `CHUNK_SIZE` in `add_urls_to_qdrant.py`

---

## Support Files

### Main Scripts

| File | Purpose | Usage |
|------|---------|-------|
| `docs_server.py` | HTTP server for local documentation | `python3 docs_server.py /path/to/docs` |
| `local_docs_url_generator.py` | Generate URL list from filesystem | `python3 local_docs_url_generator.py /path/to/docs -o urls.txt` |
| `add_urls_to_qdrant.py` | Index documents to Qdrant | `python3 add_urls_to_qdrant.py urls.txt` |
| `reset_qdrant.py` | Reset Qdrant collection | `python3 reset_qdrant.py` |

### Test Scripts (optional)

| File | Purpose |
|------|---------|
| `query_ragdocs.py` | Test direct queries to Qdrant (bypass MCP) |
| `test_ragdocs.py` | Complete system test |

---

## Metadata Architecture

Each indexed document has the following structure in Qdrant:

```json
{
  "id": "uuid-random",
  "vector": [0.123, 0.456, ...],  // 768 dimensions
  "payload": {
    "_type": "DocumentChunk",
    "text": "Chunk content...",
    "url": "http://localhost:8000/path/to/file.md",
    "title": "Document title",
    "timestamp": "2025-11-14T12:00:00.000000",
    "chunk_index": 0,
    "total_chunks": 5
  }
}
```

**Required fields** (required by MCP server):
- `_type`: Must be `"DocumentChunk"`
- `text`: Text content
- `url`: Source URL
- `title`: Title
- `timestamp`: ISO 8601 timestamp

---

## License and Credits

- **Qdrant**: [Apache 2.0](https://github.com/qdrant/qdrant)
- **Ollama**: [MIT](https://github.com/ollama/ollama)
- **@qpd-v/mcp-server-ragdocs**: Check package license

---

## Support and Contributions

For issues or suggestions, open an issue in the project repository.

**Documentation version**: 1.0  
**Last update**: November 2025
