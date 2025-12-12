# Ragify - Self-Hosted RAG Container

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Container](https://img.shields.io/badge/Container-GHCR-blue.svg)](https://ghcr.io/strawberry-code/ragify)

![Ragify Dashboard](assets/dashboard.png)

All-in-one container for semantic document search. Index your docs, search with AI embeddings.

**Includes:** Ollama + nomic-embed-text, Qdrant vector DB, Apache Tika, REST API, Web UI, MCP server.

## Quick Start

```bash
docker pull ghcr.io/strawberry-code/ragify:latest
docker run -d --name ragify -p 8080:8080 -v ragify_data:/data \
  ghcr.io/strawberry-code/ragify:latest
```

Open http://localhost:8080 - upload files and search.

## Supported Formats

PDF, DOCX, XLSX, PPTX, ODT, RTF, EPUB, TXT, MD, JSON, YAML, XML, HTML, and 1000+ more via Apache Tika.

All code files: `.py`, `.js`, `.ts`, `.java`, `.go`, `.rs`, `.c`, `.cpp`, etc.

## Production Setup with OAuth

For production, enable GitHub OAuth to restrict access.

### 1. Create GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Set:
   - **Application name:** Ragify
   - **Homepage URL:** `https://your-domain.com`
   - **Authorization callback URL:** `https://your-domain.com/oauth/github-callback`
4. Copy Client ID and Client Secret

### 2. Configuration Files

**docker-compose.yml**
```yaml
services:
  ragify:
    image: ghcr.io/strawberry-code/ragify:latest
    container_name: ragify
    ports:
      - "8080:8080"
    volumes:
      - ragify_data:/data
      - ./users.yaml:/config/users.yaml:ro
    env_file:
      - .env
    restart: unless-stopped

volumes:
  ragify_data:
```

**users.yaml** - Authorized GitHub usernames
```yaml
authorized_users:
  - username: your-github-username
  - username: teammate-username
```

**.env** - Environment variables
```bash
AUTH_CONFIG=/config/users.yaml
GITHUB_CLIENT_ID=Ov23li...
GITHUB_CLIENT_SECRET=abc123...
BASE_URL=https://your-domain.com
```

### 3. Start

```bash
docker compose up -d
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_CONFIG` | - | Path to users.yaml (enables OAuth) |
| `GITHUB_CLIENT_ID` | - | GitHub OAuth App Client ID |
| `GITHUB_CLIENT_SECRET` | - | GitHub OAuth App Secret |
| `BASE_URL` | `http://localhost:8080` | Public URL for OAuth callbacks |
| `API_PORT` | `8080` | API and Web UI port |
| `OLLAMA_MODEL` | `nomic-embed-text` | Embedding model |
| `CHUNK_SIZE` | `400` | Target chunk size in tokens |
| `CHUNK_MAX_TOKENS` | `1500` | Maximum chunk size |
| `EMBEDDING_BATCH_SIZE` | `20` | Max chunks per embedding API call |
| `EMBEDDING_TOKEN_BUDGET` | `1800` | Max tokens per batch (dynamic batching) |

## Features

### Web UI
- Upload files via drag & drop
- Create and manage collections
- Search with semantic results
- View indexing job status

### REST API
```bash
# List collections
curl http://localhost:8080/api/collections

# Search
curl -X POST http://localhost:8080/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to configure", "collection": "docs", "limit": 5}'

# Upload file
curl -X POST http://localhost:8080/api/upload \
  -F "file=@document.pdf" \
  -F "collection=docs"
```

### MCP Server (Claude Desktop / Claude Code)

The container exposes an MCP endpoint for Claude integration.

**Claude Code config** (`~/.claude.json`):
```json
{
  "mcpServers": {
    "ragify": {
      "type": "streamable-http",
      "url": "https://your-domain.com/mcp/sse",
      "headers": {
        "Authorization": "Bearer <your-oauth-token>"
      }
    }
  }
}
```

## Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RAGIFY PIPELINE                               │
│                                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐   │
│  │  Upload  │───►│  Tika    │───►│ Chunking │───►│  Embedding   │   │
│  │  (file)  │    │ Server   │    │ Semantic │    │ nomic-embed  │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────┬───────┘   │
│                                                          │          │
│                                                          ▼          │
│  ┌──────────┐    ┌──────────┐                    ┌──────────────┐   │
│  │  Search  │◄───│  Qdrant  │◄───────────────────│    Store     │   │
│  │  Query   │    │  Vector  │                    │   Vectors    │   │
│  └──────────┘    └──────────┘                    └──────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Pipeline Steps

1. **Upload** - Files uploaded via Web UI or API
2. **Extraction** - Apache Tika server extracts text from all formats
3. **Chunking** - Semantic chunking with token validation
4. **Embedding** - Dynamic batching for optimal throughput
5. **Storage** - Vectors stored in Qdrant with indexed file hash
6. **Deduplication** - O(1) hash lookup prevents re-indexing

## Health Check

```bash
curl http://localhost:8080/health
# {"status": "healthy", "ollama": "ok", "qdrant": "ok"}
```

## Volumes

| Path | Description |
|------|-------------|
| `/data` | Qdrant storage (persist this!) |
| `/config/users.yaml` | Authorized users (read-only) |
| `/tmp/collections` | Uploaded files (temporary, 15-day retention) |

## CLI Access (Inside Container)

```bash
docker exec -it ragify bash

# Index a directory
python3 ragify.py index /data/docs

# Query
python3 ragify.py query "search term"

# List collections
python3 ragify.py list
```

## Troubleshooting

### Container won't start
```bash
docker logs ragify
```
Check for:
- Missing `AUTH_CONFIG` when OAuth env vars are set
- Invalid `users.yaml` format

### Slow indexing
The container includes optimized batching. Check:
- `EMBEDDING_BATCH_SIZE` (default 20)
- `EMBEDDING_TOKEN_BUDGET` (default 1800)

### OAuth callback error
Verify `BASE_URL` matches your actual domain and GitHub OAuth App callback URL.

## License

MIT License - See [LICENSE](LICENSE)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.
