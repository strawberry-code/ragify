# Documentation

This directory contains detailed documentation for the RAG platform components.

## Ragify - Automated RAG Pipeline

**[📖 Ragify Documentation](RAGIFY.md)** - Complete guide for the automated document indexing pipeline

**[⚡ Quick Guide](QUICK_GUIDE.md)** - Quick reference for all ragify commands

## MCP Integration

**[🔌 MCP Setup Guide](MCP_SETUP.md)** - Configure MCP Server ragdocs for Claude Desktop/Crush CLI

## What is Ragify?

Ragify is an automated pipeline for indexing local documentation into Qdrant for RAG (Retrieval-Augmented Generation). It processes documents directly from your filesystem without needing an HTTP server.

### Key Features

- 📁 **Direct File Processing** - No HTTP server needed
- 🌐 **Universal Format Support** - 1000+ formats via Apache Tika
- 🔍 **Smart Deduplication** - SHA-256 hash-based incremental updates
- ⚡ **Type-Specific Chunking** - Optimized for different file types
- 📊 **Detailed Reporting** - Comprehensive statistics and logs

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Index your documentation
python3 ragify.py index ./docs

# Query indexed documents
python3 ragify.py query "authentication"

# List indexed files
python3 ragify.py list
```

For complete documentation, see [RAGIFY.md](RAGIFY.md)
