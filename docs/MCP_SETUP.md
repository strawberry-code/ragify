# MCP Server - Setup Guide

This guide shows how to configure MCP servers to query your indexed documentation from MCP-compatible clients like Claude Desktop or Claude Code.

## Server Options

| Server | Language | Multiple Collections | Distribution |
|--------|----------|---------------------|--------------|
| **Ragify MCP** (recommended) | Python | Yes | uvx / PyPI |
| ragdocs (legacy) | Node.js | No | npm |

---

## Ragify MCP Server (Recommended)

The Ragify MCP server supports multiple collections and is distributed as a Python package.

### Prerequisites

- [uv](https://github.com/astral-sh/uv) installed (for uvx)
- Qdrant running with indexed documentation
- Ollama running with nomic-embed-text model

### Installation (uvx)

**No installation needed!** uvx downloads and runs the package automatically.

```bash
# Install uv (one time)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Configuration

Add to your MCP config:
- **Claude Code**: `.mcp.json` in project root
- **Claude Desktop**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

> **Note**: `.mcp.json` is gitignored to protect secrets. Copy from template:
> ```bash
> cp .mcp.json.example .mcp.json
> # Edit .mcp.json with your API keys
> ```

#### Option A: From PyPI (recommended)
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

#### Option B: From local directory (development)
```json
{
  "mcpServers": {
    "ragify": {
      "command": "uvx",
      "args": ["--from", "/path/to/ragify", "ragify-mcp"],
      "env": {
        "QDRANT_URL": "http://127.0.0.1:6333",
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

Replace `/path/to/ragify` with your actual path.

### Available Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `search_documentation` | `query`, `collection`, `limit` | Semantic search in a collection |
| `list_collections` | - | List all available collections |
| `list_sources` | `collection` | List files in a collection |

### Usage Examples

In Claude Desktop or Claude Code:

- "Search for authentication in the matematica collection"
- "List all available collections"
- "What files are indexed in the fisica collection?"

### Development & Testing

```bash
# Test locally with uvx
uvx --from . ragify-mcp

# Or install in development mode
pip install -e .
ragify-mcp

# Test with MCP Inspector
pip install "mcp[cli]"
mcp dev src/ragify_mcp/server.py
```

---

## ragdocs (Legacy)

The original npm-based MCP server. **Note:** This server only supports a single hardcoded collection.

### Installation

```bash
npm install -g @qpd-v/mcp-server-ragdocs
```

### Configuration

```json
{
  "mcpServers": {
    "ragdocs": {
      "command": "/path/to/node",
      "args": ["/path/to/node_modules/@qpd-v/mcp-server-ragdocs/build/index.js"],
      "env": {
        "QDRANT_URL": "http://127.0.0.1:6333",
        "QDRANT_COLLECTION": "documentation",
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

---

## Remote Qdrant with API Key

You can run Qdrant on a remote server and query it from your local MCP client.

### 1. Server Setup (Ubuntu/Remote)

```bash
# Run Qdrant with API key authentication
docker run -d --name qdrant --restart unless-stopped \
  -p 6333:6333 \
  -e QDRANT__SERVICE__API_KEY=your-secret-api-key \
  -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

### 2. Local MCP Configuration

```json
{
  "mcpServers": {
    "ragify": {
      "command": "uvx",
      "args": ["ragify-mcp"],
      "env": {
        "QDRANT_URL": "http://your-server-ip:6333",
        "QDRANT_API_KEY": "your-secret-api-key",
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

### 3. Security Recommendations

- **HTTPS**: Use a reverse proxy (nginx/Caddy) with SSL in front of Qdrant
- **Firewall**: Restrict port 6333 to known IPs
- **VPN/Tunnel**: Consider SSH tunnel or VPN for added security
  ```bash
  # SSH tunnel example (run locally)
  ssh -L 6333:localhost:6333 user@your-server
  ```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | http://localhost:6333 | Qdrant server URL |
| `QDRANT_API_KEY` | - | Optional API key for Qdrant Cloud |
| `OLLAMA_URL` | http://localhost:11434 | Ollama server URL |

---

## Working with Multiple Collections

Index documents into different collections:

```bash
python3 ragify.py index ./docs/matematica    # Creates collection "matematica"
python3 ragify.py index ./docs/fisica        # Creates collection "fisica"

# Or specify collection manually
python3 ragify.py index ./docs --collection my_custom_name
```

Query specific collections in Claude:

```
"Search for 'integral' in the matematica collection"
"List all sources in fisica"
```

---

## Troubleshooting

### MCP Server not appearing

1. Restart your MCP client after config changes
2. Check environment variables are set correctly
3. Verify uv is installed: `uv --version`

### Connection errors

```bash
# Test Qdrant
curl http://localhost:6333/collections

# Test Ollama
curl http://localhost:11434/api/tags
```

### Collection not found

Index documents first:

```bash
python3 ragify.py index ./docs
python3 ragify.py list  # Verify indexing
```

---

## Publishing to PyPI (for maintainers)

```bash
# Build
pip install build
python -m build

# Upload to PyPI
pip install twine
twine upload dist/*
```

---

## More Information

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [uv Documentation](https://github.com/astral-sh/uv)
