# ragify-mcp

MCP Server for semantic documentation search using Qdrant and Ollama.

## Installation

No installation needed with uvx:

```bash
uvx ragify-mcp
```

Or install via pip:

```bash
pip install ragify-mcp
```

## Configuration

Add to your MCP client config (Claude Desktop or Claude Code):

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

## Prerequisites

- Qdrant running with indexed documentation
- Ollama running with `nomic-embed-text` model

## Available Tools

| Tool | Description |
|------|-------------|
| `search_documentation` | Semantic search in a collection |
| `list_collections` | List all available collections |
| `list_sources` | List indexed files in a collection |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | http://localhost:6333 | Qdrant server URL |
| `QDRANT_API_KEY` | - | Optional API key for Qdrant Cloud |
| `OLLAMA_URL` | http://localhost:11434 | Ollama server URL |

## Part of Ragify

This MCP server is part of the [Ragify](https://github.com/strawberry-code/self-hosted-llm-rag) project - a self-hosted RAG system for indexing and querying documentation.

## License

MIT
