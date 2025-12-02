# Contributing to Ragify

Technical documentation for contributors and developers.

## Project Structure

```
self-hosted-llm-rag/
├── ragify.py                 # Main CLI entry point
├── mcp_server.py             # MCP server entry point
├── config.yaml               # Default configuration
│
├── api/                      # FastAPI REST API
│   ├── main.py               # App initialization, lifespan, routers
│   ├── auth.py               # GitHub OAuth browser login
│   ├── oauth.py              # OAuth 2.0 Authorization Server (RFC 8414)
│   ├── routes/
│   │   ├── collections.py    # Collection CRUD
│   │   ├── upload.py         # File upload + background indexing
│   │   ├── mcp.py            # MCP SSE/Streamable HTTP transport
│   │   └── ragify.py         # Search endpoint
│   └── middleware/
│       └── auth_middleware.py # Session + Bearer token validation
│
├── lib/                      # Core library
│   ├── config.py             # RagifyConfig dataclass
│   ├── chunking.py           # Two-stage chunking (Chonkie + Semchunk)
│   ├── embedding.py          # Ollama embedding with batching
│   ├── text_cleaning.py      # Text normalization
│   ├── file_utils.py         # File scanning, hash computation
│   ├── qdrant_operations.py  # Qdrant client wrapper
│   ├── tika_check.py         # Tika availability check
│   ├── doctor.py             # System diagnostics
│   └── extractors/
│       ├── __init__.py       # Unified extraction API
│       └── tika_extractor.py # Tika + fallback extractors
│
├── src/ragify_mcp/           # MCP package (published to PyPI)
│   ├── server.py             # MCP server implementation
│   └── __init__.py
│
├── frontend/                 # Web UI (Alpine.js + HTMX)
│   ├── index.html            # SPA entry point
│   └── static/
│       ├── app.js            # Alpine.js state and methods
│       └── style.css         # 1950s control panel theme
│
├── docker/                   # Container support
│   ├── entrypoint.sh         # Startup orchestration
│   ├── healthcheck.sh        # Health check script
│   └── qdrant_config.yaml    # Qdrant configuration
│
├── Dockerfile                # Base image (no Tika)
├── Dockerfile.tika           # Full image with Java/Tika
└── .claude/commands/         # Claude Code slash commands
```

## Development Setup

### Prerequisites

- Python 3.10+
- Docker or Podman
- Ollama with `nomic-embed-text` model
- Qdrant (via Docker)

### Local Development

```bash
# 1. Clone and setup
git clone https://github.com/strawberry-code/self-hosted-llm-rag.git
cd self-hosted-llm-rag
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Start dependencies
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
ollama pull nomic-embed-text

# 3. Verify setup
python3 ragify.py doctor

# 4. Run API server
uvicorn api.main:app --reload --port 8080
```

### Environment Variables

```bash
# Required for OAuth (optional for local dev)
export GITHUB_CLIENT_ID=...
export GITHUB_CLIENT_SECRET=...
export AUTH_CONFIG=./users.yaml
export BASE_URL=http://localhost:8080

# Service URLs (defaults work for local)
export QDRANT_URL=http://localhost:6333
export OLLAMA_URL=http://localhost:11434
```

## Architecture

### Processing Pipeline

```
File Upload
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  lib/extractors/                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ PlainTextExtractor │──►│ Text content    │                   │
│  │ CodeExtractor      │    └────────┬────────┘                  │
│  │ TikaExtractor      │             │                           │
│  └─────────────────┘             │                              │
└──────────────────────────────────┼──────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  lib/chunking.py                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ semantic_chunk  │───►│ fine_chunk      │───►│ filter      │ │
│  │ (Chonkie 1024)  │    │ (Semchunk 512)  │    │ (validate)  │ │
│  └─────────────────┘    └─────────────────┘    └──────┬──────┘ │
└───────────────────────────────────────────────────────┼────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  lib/embedding.py                                                │
│  ┌─────────────────────┐    ┌─────────────────────┐             │
│  │ batch_embed_chunks  │───►│ 768-dim vectors     │             │
│  │ (Ollama nomic)      │    │ (10 chunks/batch)   │             │
│  └─────────────────────┘    └──────────┬──────────┘             │
└─────────────────────────────────────────┼───────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  lib/qdrant_operations.py                                        │
│  ┌─────────────────────┐    ┌─────────────────────┐             │
│  │ create_point        │───►│ Qdrant collection   │             │
│  │ upload_points       │    │ (vectors + payload) │             │
│  └─────────────────────┘    └─────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### Chunk Payload Schema

Each chunk stored in Qdrant contains:

```python
{
    "id": "uuid4",
    "vector": [768 floats],
    "payload": {
        "_type": "DocumentChunk",
        "text": "chunk content",
        "url": "file path or URL",
        "title": "document title",
        "timestamp": "ISO datetime",
        "chunk_index": 0,
        "total_chunks": 5,
        "semantic_block_index": 0,
        "token_count": 450,
        "chunking_method": "semantic",
        "embedding_model": "nomic-embed-text",
        "file_hash": "sha256hex"
    }
}
```

### OAuth Flow

```
Browser ─────► /auth/login ─────► GitHub OAuth
                                      │
                                      ▼
              /oauth/github-callback ◄─┘
                    │
                    ├── Valid user? ──► Set session cookie ──► Redirect to /
                    │
                    └── Invalid? ──► 403 Forbidden

MCP Client ──► /oauth/authorize ──► GitHub OAuth
                                        │
                                        ▼
              /oauth/github-callback ◄──┘
                    │
                    └── Return auth code ──► Client exchanges for token
                                                    │
                                                    ▼
              /oauth/token ◄────────────────────────┘
                    │
                    └── Return Bearer token
```

## Key Files

### `ragify.py` - CLI and Pipeline

Main entry point. Contains `RagifyPipeline` class:

```python
class RagifyPipeline:
    def __init__(self, config: RagifyConfig, use_tika: bool = True)
    def process_directory(self, directory: Path) -> dict
    def process_file(self, file_path: Path) -> bool
```

### `lib/chunking.py` - Two-Stage Chunking

```python
def semantic_chunk_text(text: str, max_tokens: int = 1024) -> list[str]
def fine_chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[dict]
def filter_chunks(chunks: list[dict], min_tokens: int = 0, max_tokens: int = 8192) -> list[dict]
```

### `lib/embedding.py` - Ollama Integration

```python
def get_embedding(text: str, model: str = "nomic-embed-text") -> list[float]
def batch_embed_chunks(chunks: list[dict], batch_size: int = 10) -> list[dict]
```

### `api/routes/mcp.py` - MCP Transport

Implements both SSE (GET) and Streamable HTTP (POST):

```python
@router.get("/sse")   # SSE for long-lived connections
@router.post("/sse")  # Streamable HTTP for Claude Code
```

## Testing

```bash
# Run CLI tests
python3 ragify.py doctor --fix

# Test indexing
python3 ragify.py index ./test_docs --collection test

# Test query
python3 ragify.py query "test query" --collection test

# Test API
curl http://localhost:8080/health
curl http://localhost:8080/api/collections
```

## Building Docker Images

```bash
# Base image (text/code only)
podman build -t ragify:latest -f Dockerfile .

# Tika image (all formats)
podman build -t ragify:latest-tika -f Dockerfile.tika .

# For deployment (amd64)
podman build --platform linux/amd64 -f Dockerfile.tika \
  -t ghcr.io/strawberry-code/ragify:latest-tika .
```

## Commit Guidelines

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(api): add new endpoint for batch upload
fix(chunking): handle empty documents
docs(readme): update installation steps
refactor(lib): simplify embedding batch logic
```

Scopes: `api`, `lib`, `frontend`, `docker`, `mcp`, `cli`, `docs`

## Claude Code Commands

Use these slash commands for common operations:

- `/commit` - Commit with conventional changelog
- `/build` - Build Docker images
- `/push-ghcr` - Push to GitHub Container Registry
- `/release` - Full release workflow

## Common Tasks

### Adding a New API Endpoint

1. Create route in `api/routes/`
2. Register in `api/main.py`
3. Add to auth middleware whitelist if public

### Adding a New Extractor

1. Create class in `lib/extractors/`
2. Implement `can_handle(path)` and `extract(path)` methods
3. Register in `lib/extractors/__init__.py`

### Modifying Chunking Strategy

Edit `lib/chunking.py`:
- `semantic_chunk_text()` for macro-level
- `fine_chunk_text()` for fine-grained
- `filter_chunks()` for validation

## Resources

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [FastAPI](https://fastapi.tiangolo.com/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Apache Tika](https://tika.apache.org/)
