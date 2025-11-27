# MCP Server - Setup Guide

This guide shows how to configure MCP servers to query your indexed documentation from MCP-compatible clients like Claude Desktop or Claude Code.

## Server Options

There are two MCP server options:

| Server | Language | Multiple Collections | Description |
|--------|----------|---------------------|-------------|
| **Ragify MCP** (recommended) | Python | Yes | Native integration with ragify.py |
| ragdocs (legacy) | Node.js | No | Third-party npm package |

---

## Option 1: Ragify MCP Server (Recommended)

The new native MCP server integrates directly with ragify and supports multiple collections.

### Prerequisites

- Python 3.10+
- Qdrant running with indexed documentation
- Ollama running with nomic-embed-text model

### Installation

```bash
cd /path/to/self-hosted-llm-rag
pip install -r requirements.txt  # Includes mcp[cli]>=1.0.0
```

### Configuration for Claude Desktop / Claude Code

Add to your MCP config:
- **Claude Code**: `.mcp.json` in project root
- **Claude Desktop**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "ragify": {
      "command": "/path/to/self-hosted-llm-rag/.venv/bin/python3",
      "args": ["/path/to/self-hosted-llm-rag/mcp_server.py"],
      "env": {
        "QDRANT_URL": "http://127.0.0.1:6333",
        "OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

**Important:** Use the full path to the Python interpreter in the project's virtual environment (`.venv/bin/python3`), not just `python3`. This ensures the `mcp` module is found.

Replace `/path/to/self-hosted-llm-rag` with your actual path.

### Available Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `search_documentation` | `query`, `collection`, `limit` | Semantic search in a collection |
| `list_collections` | - | List all available collections |
| `list_sources` | `collection` | List files in a collection |

### Usage Examples

In Claude Desktop or Claude Code, you can use:

- "Search for authentication in the matematica collection"
- "List all available collections"
- "What files are indexed in the fisica collection?"

### Development & Testing

```bash
# Test with MCP Inspector
pip install "mcp[cli]"
mcp dev mcp_server.py

# In the Inspector, test tools:
# - list_collections()
# - search_documentation("your query", "collection_name", 5)
# - list_sources("collection_name")
```

---

## Option 2: ragdocs (Legacy)

The original npm-based MCP server. **Note:** This server only supports a single hardcoded collection.

### Installation

```bash
npm install -g @qpd-v/mcp-server-ragdocs
```

### Configuration for Claude Desktop

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

**Finding paths:**

```bash
# Find node path
which node

# Find global node_modules
npm root -g
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

With Ragify MCP, you can work with multiple collections:

```bash
# Index documents into different collections
python3 ragify.py index ./docs/matematica    # Creates collection "matematica"
python3 ragify.py index ./docs/fisica        # Creates collection "fisica"
python3 ragify.py index ./docs/chimica       # Creates collection "chimica"

# Or specify collection manually
python3 ragify.py index ./docs --collection my_custom_name
```

Then query specific collections:

```
# In Claude Desktop/Code
"Search for 'integral' in the matematica collection"
"List all sources in fisica"
```

---

## Troubleshooting

### MCP Server not appearing

1. Verify paths are correct (absolute paths required)
2. Check environment variables are set correctly
3. Restart your MCP client

### Connection errors

```bash
# Test Qdrant
curl http://localhost:6333/collections

# Test Ollama
curl http://localhost:11434/api/tags
```

### Collection not found

Make sure you've indexed documents with ragify first:

```bash
python3 ragify.py index ./docs
python3 ragify.py list  # Verify indexing
```

---

## More Information

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [Ragify Documentation](RAGIFY.md)
