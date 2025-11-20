# Ragify Quick Guide

## Commands

### `ragify.py doctor`
Check system prerequisites
- `--fix` - Auto-install missing Python packages

### `ragify.py init-config`
Create default configuration file
- `--path PATH` - Config file path (default: config.yaml)

### `ragify.py index DIRECTORY`
Index all documents from a directory into Qdrant
- `--config FILE` - Use custom config file
- `--chunk-size N` - Override chunk size in tokens
- `--overlap N` - Override chunk overlap in tokens
- `--batch-size N` - Override batch upload size
- `--collection NAME` - Override collection name
- `-v, --verbose` - Enable verbose output
- `--no-tika` - Skip Tika (text/code files only)
- `--non-interactive` - No prompts (for CI/CD)

### `ragify.py query QUERY`
Search indexed documents
- `--limit N` - Number of results (default: 5)
- `--collection NAME` - Collection name (default: documentation)

### `ragify.py list`
List all indexed documents with statistics
- `--collection NAME` - Collection name (default: documentation)

### `ragify.py reset`
Reset (delete and recreate) Qdrant collection
- `--collection NAME` - Collection name (default: documentation)
- `--confirm` - Skip confirmation prompt

## Environment Variables
```bash
export OLLAMA_URL=http://localhost:11434
export QDRANT_URL=http://localhost:6333
export QDRANT_API_KEY=your-key  # optional
```

## Quick Start
```bash
# 0. Check prerequisites
python3 ragify.py doctor

# 1. Create config
python3 ragify.py init-config

# 2. Index documents
python3 ragify.py index ./docs

# 3. Query documents
python3 ragify.py query "authentication"

# 4. List indexed files
python3 ragify.py list

# 5. Reset collection
python3 ragify.py reset
```

## File Processing
- **With Tika**: PDF, DOCX, MD, HTML, TXT, code (1000+ formats)
- **Without Tika (--no-tika)**: MD, TXT, JSON, YAML, code files only
- **Skipped**: Hidden files, binaries, __pycache__, node_modules
- **Deduplication**: SHA-256 hash, skips unchanged files