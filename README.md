# RAG Platform - Self-Hosted Documentation Search

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> 🇮🇹 **Versione Italiana**: [README.it.md](README.it.md)

A complete RAG (Retrieval-Augmented Generation) platform for indexing and searching local documentation using semantic search with vector embeddings.

## Quick Start

### 1. Check Prerequisites

```bash
python3 ragify.py doctor
```

This verifies:
- Python 3.10+ and dependencies
- Java (for Apache Tika)
- Ollama with nomic-embed-text model
- Qdrant vector database
- Disk space

Use `--fix` to auto-install missing Python packages.

### 2. Index Your Documentation

```bash
python3 ragify.py index ./docs         # → collection "docs"
```

Ragify will:
- Extract text from 1000+ file formats (PDF, DOCX, MD, code files)
- Split into semantic chunks
- Generate embeddings with Ollama
- Store in Qdrant for fast retrieval

**Multiple collections**: The folder name becomes the collection name automatically. This allows you to organize content by topic and avoid bias in search results - querying a physics collection won't return unrelated math results:

```bash
python3 ragify.py index ./physics      # → collection "physics"
python3 ragify.py index ./math         # → collection "math"
python3 ragify.py index ./docs --collection custom  # → explicit name
```

### 3. Query Your Docs

```bash
python3 ragify.py query "how does authentication work?"
python3 ragify.py query "integral calculus" --collection math
```

**📖 Full documentation**: [docs/RAGIFY.md](docs/RAGIFY.md) | **⚡ Quick reference**: [docs/QUICK_GUIDE.md](docs/QUICK_GUIDE.md)

---

## What is Ragify?

**Ragify** is an automated pipeline for indexing local documentation:

- ✅ **No HTTP server** - Direct filesystem access
- ✅ **Universal formats** - PDF, DOCX, code, markdown (via Apache Tika)
- ✅ **Smart deduplication** - SHA-256 hash-based incremental updates
- ✅ **Semantic chunking** - Type-specific strategies per file format
- ✅ **All-in-one CLI** - Index, query, list, reset commands

### How It Works

```
Local Documents
    ↓
[ragify index] → Extract text, chunk, embed
    ↓
[Ollama nomic-embed-text] → Generate vectors (768-dim)
    ↓
[Qdrant] → Store vectors + metadata
    ↓
[ragify query] → Semantic search
```

---

## Installation

### Prerequisites

1. **Docker** - For Qdrant vector database
2. **Ollama** - For embeddings ([ollama.ai](https://ollama.ai/))
3. **Python 3.10+** - With pip
4. **Java 8+** - For Apache Tika (optional but recommended)

### Setup

```bash
# 1. Start Qdrant
docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# 2. Install Ollama and pull model
ollama pull nomic-embed-text

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Verify system
python3 ragify.py doctor
```

---

## MCP Integration (Optional)

Query your indexed docs from Claude Desktop or Claude Code via MCP.

### Install

No installation needed - uses [uvx](https://github.com/astral-sh/uv):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Configure

Add to your MCP config:
- **Claude Code**: `.mcp.json` in project root
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

**📖 Detailed MCP setup**: [docs/MCP_SETUP.md](docs/MCP_SETUP.md)

---

## Components

- **Ragify** - Document indexing CLI (Python)
- **Qdrant** - Vector database (Docker)
- **Ollama** - Local embeddings (nomic-embed-text, 768-dim)
- **[ragify-mcp](https://pypi.org/project/ragify-mcp/)** - MCP server for Claude Desktop/Code (optional)

---

## Documentation

- **[Ragify Documentation](docs/RAGIFY.md)** - Complete guide
- **[Quick Reference](docs/QUICK_GUIDE.md)** - Command cheatsheet
- **[MCP Setup](docs/MCP_SETUP.md)** - Claude Desktop integration

---

## Environment Variables

```bash
export OLLAMA_URL=http://localhost:11434
export QDRANT_URL=http://localhost:6333
export QDRANT_API_KEY=your-key  # Optional, for Qdrant Cloud
```

---

## License

MIT License - See [LICENSE](LICENSE)

---

## Contributing

This is a personal project. Feel free to fork and adapt for your needs.
