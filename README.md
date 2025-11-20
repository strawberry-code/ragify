# RAG Platform - Complete Documentation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> 🇮🇹 **Versione Italiana**: [README.it.md](README.it.md)

## Quick Start

### Step 1: Check Prerequisites 🩺

Run the doctor command to verify your system is ready:

```bash
python3 ragify.py doctor
```

This will check:
- ✓ Python 3.10+ and dependencies
- ✓ Java (for Apache Tika)
- ✓ Ollama running with nomic-embed-text model
- ✓ Qdrant vector database
- ✓ Disk space

Use `--fix` flag to auto-install missing Python packages:

```bash
python3 ragify.py doctor --fix
```

### Step 2: Start Using Ragify

```bash
# Index your documentation
python3 ragify.py index ./docs

# Query indexed documents
python3 ragify.py query "authentication"
```

**📖 Full documentation**: [docs/RAGIFY.md](docs/RAGIFY.md)

### Manual Installation

Follow the [Installation from Scratch](#installation-from-scratch) section below.

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Components and Architecture](#components-and-architecture)
3. [Ragify - Modern Document Indexing](#ragify---modern-document-indexing)
4. [System Requirements](#system-requirements)
5. [Installation from Scratch](#installation-from-scratch)
6. [Importing Documentation](#importing-documentation)
7. [Usage and Queries](#usage-and-queries)
8. [Maintenance](#maintenance)

---

## System Overview

This RAG (Retrieval-Augmented Generation) platform allows you to index local documentation and query it using semantic search with vector embeddings.

### How It Works

The system converts text documents into vector representations (embeddings) and stores them in a vector database. When you perform a query, the system:

1. **Converts the query** into a vector embedding using the same model
2. **Searches for the most similar documents** in the vector database using cosine similarity
3. **Returns the most relevant results** with relevance scores

### Data Flow

**Modern Approach (Ragify):**
```
Local Documents
    ↓
[ragify index] → Direct file access, chunks, generates embeddings
    ↓
[Ollama - nomic-embed-text] → Generates vectors (768 dimensions)
    ↓
[Qdrant] → Stores vectors + metadata
    ↓
[ragify query] → Semantic search
```

**Legacy Approach (URL-based):**
```
Local Documents → [docs_server.py] → [local_docs_url_generator.py]
    → [add_urls_to_qdrant.py] → [Qdrant]
```

---

## Ragify - Modern Document Indexing

**Ragify** is the modern, streamlined approach to indexing documentation. It replaces the three-step HTTP server workflow with direct filesystem access.

### Why Ragify?

- ✅ **No HTTP server needed** - Direct file access
- ✅ **Universal format support** - PDF, DOCX, code, markdown (1000+ formats via Apache Tika)
- ✅ **Smart deduplication** - SHA-256 hash-based incremental updates
- ✅ **Type-specific chunking** - Optimized strategies per file type
- ✅ **All-in-one tool** - Index, query, list, and reset in one CLI

### Quick Start with Ragify

```bash
# Index a directory
python3 ragify.py index ./docs

# Query indexed documents
python3 ragify.py query "authentication"

# List all indexed files
python3 ragify.py list
```

**📖 Full documentation**: [docs/RAGIFY.md](docs/RAGIFY.md) | **⚡ Quick reference**: [docs/QUICK_GUIDE.md](docs/QUICK_GUIDE.md)

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
- **Purpose**: Downloads documents, chunks them using semantic analysis, generates embeddings and loads them to Qdrant
- **Chunking Strategy**: Two-level semantic chunking
  - **Level 1 (Chonkie)**: Semantic macro-blocks (~512 tokens) respecting document structure
  - **Level 2 (semchunk)**: Fine-grained chunks (400-600 tokens) optimized for embeddings
  - **Token-based**: Uses tiktoken for accurate token counting
  - **Auto re-chunking**: Oversized chunks automatically split to fit model limits (8192 tokens)
- **Fallback mechanisms**: If semantic libraries unavailable, gracefully degrades to character-based chunking
- **CLI Options**:
  - `--chunk-size`: Target chunk size in tokens (default: 512)
  - `--overlap`: Overlap between chunks in tokens (default: 51)
  - `--verbose`: Detailed logging
- **Metadata**:
  - `_type`: "DocumentChunk" (required by MCP)
  - `text`: Chunk content
  - `url`: Source URL
  - `title`: Document title
  - `timestamp`: Indexing date
  - `chunk_index`: Chunk index
  - `total_chunks`: Total chunks in document
  - `semantic_block_index`: Macro-block from Level 1 chunking
  - `token_count`: Actual token count
  - `chunking_method`: Method used ('semantic', 'fallback', etc.)
  - `embedding_model`: Model used for embeddings

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
   - Version 3.10 or higher (required for semantic chunking)
   - Libraries: see `requirements.txt`

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
# Verify Python version (3.10+ required)
python3 --version

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

**Required packages** (from `requirements.txt`):
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `qdrant-client` - Qdrant vector database client
- `chonkie>=0.1.0` - Semantic macro-chunking
- `semchunk>=2.0.0` - Fine-grained semantic chunking
- `tiktoken>=0.5.0` - Token counting for OpenAI models

### Step 6: Download Support Scripts

Clone this repository or copy these files to your working directory:

**Core scripts:**
- `docs_server.py` - HTTP server for documentation
- `local_docs_url_generator.py` - URL generator from filesystem
- `add_urls_to_qdrant.py` - Indexing script with semantic chunking
- `reset_qdrant.py` - Reset Qdrant collection

**Library modules** (`lib/` package):
- `lib/text_cleaning.py` - Text normalization and quality validation
- `lib/chunking.py` - Two-level semantic chunking engine
- `lib/embedding.py` - Embedding generation with auto re-chunking
- `lib/qdrant_operations.py` - Qdrant database operations

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
# Load documents to Qdrant with semantic chunking (recommended)
python3 add_urls_to_qdrant.py urls.txt

# Advanced usage with custom parameters
python3 add_urls_to_qdrant.py urls.txt --chunk-size 600 --overlap 60 --verbose
```

**CLI Options**:
- `--chunk-size SIZE`: Target chunk size in tokens (default: 512)
- `--overlap SIZE`: Overlap between chunks in tokens (default: 51, ~10%)
- `--verbose`: Show detailed processing information

**Output**:
```
📚 Starting document indexing pipeline
================================================================================
Input file: urls.txt
Chunk size: 512 tokens | Overlap: 51 tokens
================================================================================

[1/125] Processing: http://localhost:8000/getting-started.md
  ✓ Downloaded (2,431 chars)
  ✓ Cleaned (2,387 chars after normalization)
  ✓ Semantic chunking: 1 macro-block → 3 fine chunks
  ✓ Token stats: avg=445, min=412, max=487 tokens
  ✓ Embeddings generated and uploaded

[2/125] Processing: http://localhost:8000/api/overview.md
...

================================================================================
📊 Indexing Statistics
================================================================================
URLs processed:     125 / 125 (100.0%)
Total characters:   1,245,890 (raw) → 1,238,122 (cleaned)
Macro-blocks:       387 semantic blocks
Final chunks:       1,847 embedding-ready chunks
Token distribution: avg=478, min=402, max=598 tokens
Success rate:       98.4% (123 success, 2 failed)
Total time:         4m 18s
================================================================================
```

**What happens during indexing**:
1. **Download**: Fetches HTML content from each URL
2. **Text extraction**: Extracts text using BeautifulSoup
3. **Cleaning**: Unicode normalization, whitespace cleanup, boilerplate removal
4. **Quality validation**: Checks minimum length and character diversity
5. **Semantic chunking (Level 1)**: Chonkie creates macro-blocks respecting document structure
6. **Fine chunking (Level 2)**: semchunk splits blocks into embedding-optimal sizes
7. **Token validation**: Ensures all chunks fit within model limits (8192 tokens)
8. **Embedding generation**: Creates vectors using Ollama nomic-embed-text
9. **Upload**: Stores vectors + metadata in Qdrant

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
3. **Adjust chunk size**: Re-index with different `--chunk-size` parameter
   ```bash
   python3 add_urls_to_qdrant.py urls.txt --chunk-size 400  # Smaller chunks
   python3 add_urls_to_qdrant.py urls.txt --chunk-size 600  # Larger chunks
   ```
4. **Check chunking method**: Review logs to ensure semantic chunking is working (not falling back to character-based)

#### Semantic chunking not working

If you see "Chonkie not available, using fallback" in logs:

1. **Verify Python version**: Must be 3.10 or higher
   ```bash
   python3 --version
   ```
2. **Reinstall dependencies**:
   ```bash
   pip install --upgrade chonkie semchunk tiktoken
   ```
3. **Check import errors**:
   ```bash
   python3 -c "import chonkie; import semchunk; import tiktoken; print('All OK')"
   ```

---

## Support Files

### Main Scripts

| File | Purpose | Usage |
|------|---------|-------|
| `docs_server.py` | HTTP server for local documentation | `python3 docs_server.py /path/to/docs` |
| `local_docs_url_generator.py` | Generate URL list from filesystem | `python3 local_docs_url_generator.py /path/to/docs -o urls.txt` |
| `add_urls_to_qdrant.py` | Index documents with semantic chunking | `python3 add_urls_to_qdrant.py urls.txt [--chunk-size SIZE] [--overlap SIZE] [--verbose]` |
| `reset_qdrant.py` | Reset Qdrant collection | `python3 reset_qdrant.py` |

### Library Modules (`lib/` package)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `lib/text_cleaning.py` | Text normalization and quality validation | `clean_text()`, `remove_boilerplate()`, `validate_text_quality()` |
| `lib/chunking.py` | Two-level semantic chunking | `semantic_chunk_text()`, `fine_chunk_text()`, `count_tokens()`, `validate_chunk_size()` |
| `lib/embedding.py` | Embedding generation with validation | `get_embedding()`, `safe_embed_chunk()`, `batch_embed_chunks()` |
| `lib/qdrant_operations.py` | Qdrant database operations | `create_point()`, `upload_points()`, `batch_upload_chunks()` |

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
    "total_chunks": 5,
    "semantic_block_index": 0,
    "token_count": 478,
    "chunking_method": "semantic",
    "embedding_model": "nomic-embed-text"
  }
}
```

**Required fields** (required by MCP server):
- `_type`: Must be `"DocumentChunk"`
- `text`: Text content
- `url`: Source URL
- `title`: Title
- `timestamp`: ISO 8601 timestamp

**Additional fields** (semantic chunking metadata):
- `semantic_block_index`: Index of the macro-block from Level 1 chunking
- `token_count`: Actual token count for this chunk
- `chunking_method`: Chunking strategy used (`"semantic"`, `"fallback"`, etc.)
- `embedding_model`: Model used for generating embeddings

---

## License and Credits

- **Qdrant**: [Apache 2.0](https://github.com/qdrant/qdrant)
- **Ollama**: [MIT](https://github.com/ollama/ollama)
- **@qpd-v/mcp-server-ragdocs**: Check package license

---

## Support and Contributions

For issues or suggestions, open an issue in the project repository.

---

## Advanced Features

### Semantic Chunking Architecture

The platform uses a sophisticated two-level semantic chunking approach:

#### Level 1: Macro-level Chunking (Chonkie)
- **Purpose**: Divide documents into semantically coherent macro-blocks
- **Strategy**: Respects document structure (paragraphs, sections, logical breaks)
- **Target size**: ~512 tokens per block
- **Benefit**: Preserves high-level semantic context

#### Level 2: Fine-grained Chunking (semchunk)
- **Purpose**: Split macro-blocks into embedding-optimal chunks
- **Strategy**: Token-based splitting with semantic boundary awareness
- **Target size**: 400-600 tokens per chunk
- **Benefit**: Optimal for vector embeddings while maintaining semantic coherence

#### Token-based vs Character-based

**Why token-based chunking?**
- Embedding models have token limits (nomic-embed-text: 8192 tokens)
- Prevents model overflow errors
- More accurate representation of model input
- Better semantic consistency across chunks

**Automatic validation and re-chunking:**
- All chunks validated against model token limits
- Oversized chunks automatically split at 50% of max size
- Token counting using `tiktoken` (OpenAI's tokenizer)

#### Fallback Mechanisms

The system gracefully degrades if semantic libraries are unavailable:
1. **Chonkie unavailable** → Treats entire document as single macro-block
2. **Semchunk unavailable** → Falls back to character-based sliding window
3. **Both unavailable** → Simple character-based chunking (~1000 chars)

Logs indicate which method is active for transparency.

### Performance Tuning

#### Chunk Size Optimization

**Smaller chunks (300-400 tokens)**:
- ✅ More precise results
- ✅ Better for specific queries
- ❌ More chunks = larger database
- ❌ Slower indexing

**Larger chunks (500-600 tokens)**:
- ✅ More context per result
- ✅ Fewer chunks = smaller database
- ✅ Faster indexing
- ❌ Less precise matching

**Recommended starting point**: 512 tokens (balanced)

#### Overlap Configuration

**Purpose**: Prevents important information from being split across chunk boundaries

**Recommended values**:
- Minimum: 5% (`--overlap 25` for 512-token chunks)
- Default: 10% (`--overlap 51` for 512-token chunks)
- Maximum: 20% (`--overlap 102` for 512-token chunks)

Higher overlap = better boundary handling but more storage.

---

**Documentation version**: 2.0 (with semantic chunking)  
**Last update**: November 2025
