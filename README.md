# RAG Platform - Self-Hosted Documentation Search

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> 🇮🇹 **Versione Italiana**: [README.it.md](README.it.md)

A complete RAG (Retrieval-Augmented Generation) platform for indexing and searching local documentation using semantic search with vector embeddings.

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Check Prerequisites

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

### 3. Index Your Documentation

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

### 4. Query Your Docs

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

1. **Docker + Qdrant** - Vector database
   ```bash
   # Install Docker: https://docs.docker.com/engine/install/
   docker run -d --name qdrant --restart unless-stopped \
     -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
   ```
2. **Ollama** - For embeddings ([ollama.ai](https://ollama.ai/))
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull nomic-embed-text
   # Ollama runs as systemd service, starts automatically on boot
   sudo systemctl enable ollama && sudo systemctl start ollama
   ```
3. **Python 3.10+** - With pip
4. **Java 21** - For Apache Tika (optional but recommended)
   ```bash
   # Install via sdkman (https://sdkman.io)
   sudo apt install zip unzip -y   # Ubuntu/Debian
   curl -s "https://get.sdkman.io" | bash
   source "$HOME/.sdkman/bin/sdkman-init.sh"
   sdk install java 21-zulu
   ```

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

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | http://localhost:6333 | Qdrant server URL |
| `QDRANT_API_KEY` | - | API key for Qdrant authentication |
| `OLLAMA_URL` | http://localhost:11434 | Ollama server URL |

```bash
# Example: connect to remote Qdrant with API key
export QDRANT_URL=http://your-server:6333
export QDRANT_API_KEY=your-secret-key
python3 ragify.py index ./docs
```

---

## Running Long Indexing Jobs (SSH)

Use tmux to keep indexing running after disconnecting from SSH:

```bash
# Start tmux session
tmux new -s ragify

# Run indexing
source .venv/bin/activate
python3 ragify.py index ./docs

# Detach: Ctrl+B, then D
# Reconnect later: tmux attach -t ragify
```

---

## License

MIT License - See [LICENSE](LICENSE)

---

## Contributing

This is a personal project. Feel free to fork and adapt for your needs.
