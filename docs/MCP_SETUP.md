# MCP Server ragdocs - Setup Guide

This guide shows how to configure the MCP Server ragdocs to query your indexed documentation from MCP-compatible clients like Claude Desktop or Crush CLI.

## Prerequisites

- Qdrant running with indexed documentation
- Ollama running with nomic-embed-text model
- Node.js 18+ installed
- MCP-compatible client (Claude Desktop, Crush CLI, etc.)

## Installation

```bash
npm install -g @qpd-v/mcp-server-ragdocs
```

## Configuration

### For Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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
# Example output: /Users/username/.nvm/versions/node/v22.3.0/bin/node

# Find global node_modules
npm root -g
# Example output: /Users/username/.nvm/versions/node/v22.3.0/lib/node_modules
```

Replace `/path/to/node` and `/path/to/node_modules` with your actual paths.

### For Crush CLI

Add to `~/.config/claude/config.json`:

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

## Environment Variables

- `QDRANT_URL`: Qdrant server URL (default: http://127.0.0.1:6333)
- `QDRANT_COLLECTION`: Collection name (default: documentation)
- `OLLAMA_URL`: Ollama server URL (default: http://localhost:11434)
- `QDRANT_API_KEY`: Optional API key for Qdrant Cloud

## Available Functions

The MCP server provides these functions:

1. **search_documentation**: Semantic search in indexed docs
2. **add_documentation**: Add documents from URL (legacy)
3. **list_sources**: List all indexed sources
4. **test_ollama**: Test embeddings configuration

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
```

## More Information

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [ragdocs npm package](https://www.npmjs.com/package/@qpd-v/mcp-server-ragdocs)
- [Ragify Documentation](RAGIFY.md)
