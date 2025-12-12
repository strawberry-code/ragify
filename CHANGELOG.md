# Changelog

All notable changes to this project are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2025-12-12

### Breaking Changes
- **Unica immagine Docker**: rimossi `Dockerfile.tika` e `Dockerfile.tika.local`, ora esiste solo `Dockerfile` con Tika integrato
- **Tika sempre obbligatorio**: rimosso flag `--no-tika` e logica opzionale, Tika server sempre attivo
- **Tag immagine semplificato**: usare `ghcr.io/strawberry-code/ragify:latest` (rimosso suffisso `-tika`)

### Added
- **Dynamic batching**: nuovo sistema di batching basato su token budget invece di batch size fisso
- **EMBEDDING_TOKEN_BUDGET**: nuova env var (default 1800) per controllare token massimi per batch
- **Index file_hash**: creazione automatica index su Qdrant per query O(1) invece di scroll O(N)
- **FileHashCache**: cache in-memory per evitare query ripetute durante indicizzazione
- **Tika server mode**: Tika avviato come server all'avvio container (porta 9998), elimina cold start 5-10s per file

### Changed
- `EMBEDDING_BATCH_SIZE` default aumentato da 3 a 20 (ora funziona con token budget)
- Health check verifica anche Tika server oltre a API, Ollama e Qdrant
- `check_file_hash_in_qdrant()` usa `count()` O(1) invece di `scroll()` O(N)
- Entrypoint avvia Qdrant → Ollama → Tika → API in sequenza

### Removed
- `Dockerfile.tika` e `Dockerfile.tika.local`
- Flag `--no-tika` e `--non-interactive` da CLI
- Logica condizionale `use_tika` in pipeline e API

### Performance
- Riduzione chiamate embedding API: ~334 → ~50-100 per 1000 chunk
- Eliminato cold start Tika: 5-10s → 0s per file
- Hash check O(1) con index invece di O(N) scroll

## [1.3.2] - 2025-12-04

### Fixed
- Further reduced default EMBEDDING_BATCH_SIZE from 10 to 3 (batch_size × chunk_tokens must be < 2048)

## [1.3.1] - 2025-12-04

### Fixed
- Reduced default EMBEDDING_BATCH_SIZE from 32 to 10 to prevent Ollama "cannot decode batches" errors with large uploads
- New `EMBEDDING_BATCH_SIZE` env var allows tuning for different Ollama configurations

## [1.3.0] - 2025-12-04

### Changed
- Frontend semplificato: rimosso upload cartelle, ora richiede file ZIP per caricare multiple documenti
- Rimossa dipendenza JSZip dal frontend (compressione ora gestita dall'utente)

### Added
- Modale informativa quando si tenta di trascinare una cartella, con istruzioni per creare ZIP

## [1.2.3] - 2025-12-03

### Fixed
- Pinned Ollama to v0.11.0 in Dockerfiles to avoid embedding bugs in 0.12.x/0.13.x (see [ollama#13054](https://github.com/ollama/ollama/issues/13054))
- Added missing `num_ctx` option to batch embedding API call (`/api/embed`)
- Restored `max_tokens` in config.yaml to 2048 (nomic-embed-text context limit)

## [1.2.2] - 2025-12-03

### Added
- Chunking parameters now configurable via environment variables: `CHUNK_SIZE` (default 400) and `CHUNK_MAX_TOKENS` (default 1500)

### Fixed
- Reduced default chunk size to prevent Ollama panic with nomic-embed-text model (2048 token context limit)

## [1.2.1] - 2025-12-02

### Fixed
- File cleanup now guaranteed via finally block: uploaded files are deleted after Qdrant upload or on pipeline failure

## [1.2.0] - 2025-12-02

### Added
- Progress bar now shows processing stages (extracting, chunking, embedding, uploading) in real-time
- Client-side ZIP compression for multi-file uploads, reducing N HTTP requests to 1 and improving upload speed
- New `/api/upload-zip` endpoint for server-side ZIP extraction and batch processing
- Browser-side progress feedback: "Zipping..." and "Uploading..." phases before server processing

### Changed
- Batch embedding using Ollama /api/embed endpoint, reducing API calls from N to N/10 for faster uploads
- Multi-file uploads now automatically use ZIP compression (threshold: >1 file or >5MB total)

### Fixed
- Silenced verbose httpx/httpcore logs that spammed 60+ lines per file upload
- Silenced Tika startup warnings ("Failed to see startup log message; retrying...")
- Status indicators (Ollama/Qdrant/Authenticated) now wrap responsively on mobile view

## [1.1.4] - 2025-12-02

### Added
- Multi-arch Docker images support (linux/amd64 + linux/arm64) for Ubuntu and Mac compatibility
- Updated `/build` and `/push-ghcr` slash commands for multi-arch manifest workflow

### Fixed
- Dockerfile.tika Tika pre-download script now uses heredoc and handles versioned JAR names
- Removed obsolete mcp_server.py reference from Dockerfiles

## [1.1.3] - 2025-12-02

### Fixed
- Frontend API calls now include credentials for proper session authentication
- Ollama context size reduced from 8192 to 2048 to match nomic-embed-text model limit
- Centralized logging configuration for consistent pipeline logs visibility
- UI now shows actual error messages instead of generic failure messages
- Tika JAR detection now supports versioned filenames and TIKA_JAR_PATH env var
- Improved Tika pre-download in Dockerfile.tika with verification and copy to expected path

## [1.1.2] - 2025-12-02

### Changed
- Dashboard screenshot moved to `assets/` folder and embedded in README

## [1.1.1] - 2025-12-02

### Added
- Dashboard screenshot for documentation
- TODO.md with project roadmap

### Removed
- GitHub Actions workflow (manual build for now, automation planned)

## [1.1.0] - 2025-12-02

### Added
- Pre-download Tika JAR in Dockerfile.tika for PDF support on first boot
- Claude Code slash commands: `/commit`, `/build`, `/push-ghcr`, `/release`

### Changed
- Complete README.md rewrite focused on Docker container users
- New CONTRIBUTING.md with technical documentation for developers
- MCP endpoint supports both GET (SSE) and POST (Streamable HTTP)

## [1.0.0] - 2025-12-02

### Aggiunto
- OAuth 2.0 Authorization Server per MCP (RFC 8414, RFC 7591)
- Supporto Bearer token per autenticazione API e MCP
- Dynamic Client Registration per client MCP
- PKCE support (S256 e plain) per OAuth flow
- Frontend: status light "Authenticated" cliccabile con modal login GitHub
- Endpoint discovery `.well-known/oauth-authorization-server`
- Docker Compose example con configurazione OAuth
- Favicon SVG per frontend

### Modificato
- AuthMiddleware supporta sia session cookie che Bearer token
- Callback OAuth unificato per browser e MCP (`/oauth/github-callback`)
- Migliorata gestione errori nel middleware (JSONResponse invece di HTTPException)
- Aggiornato .gitignore per escludere docker-compose.yml e file sensibili

### Sicurezza
- Tutte le credenziali lette da variabili d'ambiente
- Session token firmati con itsdangerous
- CSRF protection con state parameter OAuth
- Whitelist utenti autorizzati via YAML
