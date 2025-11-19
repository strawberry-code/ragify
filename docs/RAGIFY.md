# 🚀 Ragify - Automated RAG Pipeline for Local Documentation

**Ragify** is an automated pipeline for processing local documentation and indexing it into Qdrant for RAG (Retrieval-Augmented Generation).

## ✨ Features

- 📁 **Direct File Processing**: Processes local files directly without HTTP server
- 🌐 **Universal Format Support**: Supports any format via Apache Tika (PDF, DOCX, MD, HTML, code, etc.)
- 🔍 **Smart Deduplication**: Hash-based deduplication for incremental updates
- ⚡ **Type-Specific Chunking**: Optimized chunking strategies per file type
- 📊 **Detailed Reporting**: Detailed reports in Markdown or JSON
- 🛠️ **Configurable**: Flexible configuration system with YAML
- 📈 **Progress Tracking**: Real-time progress bars with tqdm

## 🔧 Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Create default configuration
python ragify.py init-config

# Check system prerequisites
python ragify.py doctor
```

## 🚦 Prerequisites

Use `ragify doctor` to automatically check all prerequisites:

```bash
python3 ragify.py doctor
```

This verifies:
- ✅ Python 3.10+
- ✅ Python dependencies (requests, chonkie, tika, etc.)
- ✅ Java 8+ (for Apache Tika)
- ✅ Ollama running with `nomic-embed-text` model
- ✅ Qdrant vector database
- ✅ Disk space (5GB+ recommended)

**Manual setup:**

1. **Ollama** running with `nomic-embed-text` model:
   ```bash
   ollama run nomic-embed-text
   ```

2. **Qdrant** running:
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```

3. **Apache Tika** (auto-downloaded on first use)

## 📖 Usage

### Basic Usage

```bash
# Index a directory
python ragify.py index ./docs

# With custom configuration
python ragify.py index ./docs --config my-config.yaml

# With parameter overrides
python ragify.py index ./docs --chunk-size 600 --verbose
```

### Configuration

The `config.yaml` file controls all aspects of the pipeline:

```yaml
extraction:
  max_file_size: 104857600  # 100MB
  timeout: 60

chunking:
  chunk_size: 512
  overlap: 50
  strategies:
    markdown: semantic
    code: syntax_aware
    pdf: page_aware

embedding:
  provider: ollama
  model: nomic-embed-text
  batch_size: 10

qdrant:
  collection: ragify_docs
  batch_size: 10

processing:
  skip_hidden: true
  skip_patterns:
    - "*.pyc"
    - "__pycache__"
    - ".git"
    - "node_modules"
```

### Environment Variables

```bash
export OLLAMA_URL=http://localhost:11434
export QDRANT_URL=http://localhost:6333
export QDRANT_API_KEY=your-api-key  # Optional
```

### Override with Environment Variables

```bash
export RAGIFY_CHUNKING_CHUNK_SIZE=1024
export RAGIFY_EMBEDDING_BATCH_SIZE=20
```

## 📊 Output

### Processing Report

After each run, ragify generates a detailed report:

```markdown
# Ragify Processing Report

## Summary
- Date: 2024-01-15T10:30:00
- Duration: 125.3 seconds
- Success Rate: 95.2%

## Statistics
- Total Files: 150
- Processed: 143
- Skipped (unchanged): 5
- Failed: 2
- Total Chunks Created: 2,847
```

### Structured Logging

With JSON logging for programmatic analysis:

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "level": "info",
  "message": "file_processed",
  "file": "docs/api.md",
  "chunks": 23,
  "time_ms": 1250,
  "hash": "a3f5b8c2..."
}
```

## 🔄 Incremental Updates

Ragify supports incremental updates:

1. Computes SHA-256 hash of each file
2. Checks if already indexed in Qdrant
3. Skips unchanged files
4. Processes only new or modified files

## 🧩 Architecture

```
ragify.py (Main Orchestrator)
    ├── lib/extractors/ (Apache Tika Integration)
    │   ├── TikaExtractor (Universal)
    │   ├── PlainTextExtractor (Optimized)
    │   └── CodeExtractor (Source code)
    ├── lib/chunking.py (Semantic Chunking)
    │   ├── Chonkie (Level 1)
    │   └── Semchunk (Level 2)
    ├── lib/embedding.py (Ollama Integration)
    ├── lib/qdrant_operations.py (Vector DB)
    └── lib/config.py (Pydantic Validation)
```

## 🚀 Performance

- **Sequential Processing**: Reliable and predictable
- **Memory Mapping**: For large files (>10MB)
- **Batch Operations**: Batched uploads and embeddings
- **Hash Caching**: In-memory cache during run

## 📝 Supported Formats

Thanks to Apache Tika, ragify supports 1000+ formats:

- **Documents**: PDF, DOCX, ODT, RTF, EPUB
- **Code**: Python, JavaScript, Java, C++, Go, Rust
- **Data**: JSON, YAML, XML, CSV
- **Web**: HTML, XHTML, CSS
- **Text**: Markdown, reStructuredText, Plain text
- **Archives**: ZIP, TAR (extracted contents)

## 🔍 Query Documents

After indexing, you can query documents:

```bash
# Using ragify query command
python ragify.py query "how does authentication work?"

# Or via Qdrant API directly
curl -X POST 'http://localhost:6333/collections/ragify_docs/points/search' \
  -H 'Content-Type: application/json' \
  -d '{
    "vector": [...],
    "limit": 5
  }'
```

## 🛠️ Troubleshooting

### "Cannot connect to Ollama"
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags
```

### "Cannot connect to Qdrant"
```bash
# Verify Qdrant is running
curl http://localhost:6333/collections
```

### "Tika extraction failed"
```bash
# Tika requires Java 8+
java -version

# Reset Tika cache
rm -rf /tmp/tika-*
```

### Files too large
- Modify `max_file_size` in config.yaml
- Or skip with `skip_patterns`

## 📈 Migration from URL-based System

If migrating from the URL-based system:

1. **No longer need `docs_server.py`**: Ragify accesses files directly
2. **No longer need `local_docs_url_generator.py`**: Ragify scans directories
3. **Use `ragify.py` instead of `add_urls_to_qdrant.py`**

### Compatibility Mode

To maintain compatibility with existing URLs:

```python
# In process_file() of ragify.py, modify:
url=str(file_path)  # Local path

# To:
url=f"file://{file_path}"  # File URL
```

## 🚧 Roadmap

- [ ] Parallel processing with ThreadPoolExecutor
- [ ] Watch mode to monitor changes
- [ ] Integration with more embedding providers (OpenAI, Cohere)
- [ ] Web UI with Gradio/Streamlit
- [ ] Docker compose for complete setup
- [ ] Plugin system for custom extractors

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first.

## 🙏 Credits

- Apache Tika for universal extraction
- Chonkie & Semchunk for semantic chunking
- Qdrant for vector database
- Ollama for local embeddings
