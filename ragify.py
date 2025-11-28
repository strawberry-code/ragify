#!/usr/bin/env python3
"""
Ragify - Automated RAG Pipeline for Local Documentation

Main orchestrator for processing local documents and indexing them in Qdrant.
Supports multiple file formats through Apache Tika with intelligent chunking.
"""

__version__ = '1.0.0'

import warnings
# Suppress tika pkg_resources deprecation warning
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*', category=UserWarning)

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog
from tqdm import tqdm

# Import local modules
from lib import (
    batch_embed_chunks,
    batch_upload_chunks,
    check_qdrant_connection,
    clean_text,
    filter_chunks,
    fine_chunk_text,
    semantic_chunk_text,
    validate_text_quality,
)
from lib.config import RagifyConfig, create_default_config, merge_cli_args
from lib.extractors import extract_file_content, set_tika_enabled
from lib.file_utils import (
    FileHashCache,
    compute_file_hash,
    format_file_size,
    scan_directory,
)
from lib.qdrant_operations import create_point

# Try importing qdrant-client for hash checking
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models

    QDRANT_CLIENT_AVAILABLE = True
except ImportError:
    QDRANT_CLIENT_AVAILABLE = False
    logging.warning("qdrant-client not available, hash deduplication disabled")


class PipelineStats:
    """Track statistics for the pipeline run."""

    def __init__(self):
        self.total_files = 0
        self.processed_files = 0
        self.skipped_unchanged = 0
        self.failed_files = 0
        self.total_chunks = 0
        self.total_bytes = 0
        self.start_time = time.time()
        self.failed_list = []

    def duration(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time

    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100


class RagifyPipeline:
    """Main pipeline orchestrator for Ragify."""

    def __init__(self, config: RagifyConfig, use_tika: bool = True):
        """Initialize pipeline with configuration."""
        self.config = config
        self.use_tika = use_tika
        self.stats = PipelineStats()
        self.hash_cache = FileHashCache()
        self.logger = self._setup_logging()
        self.qdrant_client = self._setup_qdrant_client()

        # Configure extractors based on Tika availability
        set_tika_enabled(use_tika)
        if not use_tika:
            self.logger.info("⚠️  Running without Tika (text/code files only)")

    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging based on configuration."""
        if self.config.logging.format == "json":
            structlog.configure(
                processors=[
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.add_log_level,
                    structlog.processors.JSONRenderer()
                ],
            )
            logger = structlog.get_logger()
        else:
            logging.basicConfig(
                level=getattr(logging, self.config.logging.level.upper()),
                format='%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%H:%M:%S'
            )
            logger = logging.getLogger(__name__)

        # Also log to file if specified
        if self.config.logging.file:
            file_handler = logging.FileHandler(self.config.logging.file)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            )
            logging.getLogger().addHandler(file_handler)

        return logger

    def _setup_qdrant_client(self) -> Optional['QdrantClient']:
        """Setup Qdrant client for hash checking."""
        if not QDRANT_CLIENT_AVAILABLE:
            return None

        try:
            client = QdrantClient(
                url=self.config.qdrant.url,
                api_key=self.config.qdrant.api_key,
            )
            # Verify connection
            client.get_collections()
            return client
        except Exception as e:
            self.logger.warning(f"Qdrant client setup failed: {e}")
            return None

    def check_file_hash_in_qdrant(self, file_hash: str) -> bool:
        """
        Check if file hash exists in Qdrant.

        Args:
            file_hash: SHA-256 hash of file

        Returns:
            True if file already indexed, False otherwise
        """
        if not self.qdrant_client:
            return False

        try:
            # Search for documents with this hash
            results = self.qdrant_client.scroll(
                collection_name=self.config.qdrant.collection,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="file_hash",
                            match=models.MatchValue(value=file_hash)
                        )
                    ]
                ),
                limit=1
            )
            return len(results[0]) > 0

        except Exception as e:
            # If collection doesn't exist or other error, assume file not indexed
            if "doesn't exist" in str(e) or "Not found" in str(e):
                self.logger.debug(f"Collection {self.config.qdrant.collection} doesn't exist yet, skipping hash check")
                return False
            self.logger.debug(f"Hash check failed: {e}")
            return False

    def _ensure_collection_exists(self) -> None:
        """Ensure Qdrant collection exists, create if needed."""
        if not self.qdrant_client:
            return

        try:
            # Check if collection exists
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.config.qdrant.collection not in collection_names:
                self.logger.info(f"Creating Qdrant collection: {self.config.qdrant.collection}")

                # Create collection with proper vector config
                from qdrant_client.http import models as qmodels

                self.qdrant_client.create_collection(
                    collection_name=self.config.qdrant.collection,
                    vectors_config=qmodels.VectorParams(
                        size=768,  # nomic-embed-text dimension
                        distance=qmodels.Distance.COSINE
                    )
                )
                self.logger.info(f"✅ Collection created: {self.config.qdrant.collection}")
            else:
                self.logger.debug(f"Collection already exists: {self.config.qdrant.collection}")

        except Exception as e:
            self.logger.warning(f"Failed to ensure collection exists: {e}")

    def process_directory(self, root_path: Path) -> Dict:
        """
        Process all files in a directory.

        Args:
            root_path: Root directory to process

        Returns:
            Processing statistics
        """
        self.logger.info(f"🚀 Starting Ragify pipeline for: {root_path}")

        # Ensure Qdrant collection exists
        self._ensure_collection_exists()

        # Scan directory for files
        files = scan_directory(
            root_path,
            skip_hidden=self.config.processing.skip_hidden,
            skip_patterns=set(self.config.processing.skip_patterns),
            extensions_filter=set(self.config.processing.extensions_filter)
            if self.config.processing.extensions_filter else None
        )

        self.stats.total_files = len(files)
        self.logger.info(f"📁 Found {len(files)} files to process")

        # Process files with progress bar
        with tqdm(total=len(files), desc="Processing files", unit="file") as pbar:
            for file_path in files:
                try:
                    self.process_file(file_path, pbar)
                except Exception as e:
                    self.logger.error(f"Fatal error processing {file_path}: {e}")
                    self.stats.failed_files += 1
                    self.stats.failed_list.append((str(file_path), str(e)))
                    pbar.update(1)

        # Generate report
        self.generate_report()

        return {
            'processed': self.stats.processed_files,
            'skipped': self.stats.skipped_unchanged,
            'failed': self.stats.failed_files,
            'chunks': self.stats.total_chunks,
            'duration': self.stats.duration()
        }

    def process_file(self, file_path: Path, pbar: tqdm) -> None:
        """
        Process a single file through the pipeline.

        Args:
            file_path: Path to file
            pbar: Progress bar to update
        """
        file_size = file_path.stat().st_size
        self.stats.total_bytes += file_size

        # Skip if file too large
        if file_size > self.config.extraction.max_file_size:
            self.logger.warning(f"Skipping large file ({format_file_size(file_size)}): {file_path.name}")
            pbar.set_postfix_str(f"Skipped: {file_path.name} (too large)")
            pbar.update(1)
            return

        # 1. Compute file hash for deduplication
        file_hash = compute_file_hash(file_path)

        # Check if already indexed
        if self.check_file_hash_in_qdrant(file_hash):
            self.stats.skipped_unchanged += 1
            pbar.set_postfix_str(f"Skipped: {file_path.name} (unchanged)")
            pbar.update(1)
            return

        # 2. Extract text and metadata
        pbar.set_postfix_str(f"Extracting: {file_path.name}")
        text, metadata = extract_file_content(file_path)

        if not text:
            self.logger.warning(f"No text extracted from: {file_path.name}")
            self.stats.failed_files += 1
            self.stats.failed_list.append((str(file_path), "No text extracted"))
            pbar.update(1)
            return

        # 3. Clean text
        pbar.set_postfix_str(f"Cleaning: {file_path.name}")
        cleaned = clean_text(text)

        if not validate_text_quality(cleaned, min_length=100):
            self.logger.warning(f"Text quality too low: {file_path.name}")
            self.stats.failed_files += 1
            self.stats.failed_list.append((str(file_path), "Low text quality"))
            pbar.update(1)
            return

        # 4. Chunk text (type-specific if implemented)
        pbar.set_postfix_str(f"Chunking: {file_path.name}")
        chunks = self.chunk_by_type(cleaned, file_path)

        if not chunks:
            self.logger.warning(f"No valid chunks created: {file_path.name}")
            self.stats.failed_files += 1
            self.stats.failed_list.append((str(file_path), "Chunking failed"))
            pbar.update(1)
            return

        # 5. Generate embeddings
        pbar.set_postfix_str(f"Embedding: {file_path.name} ({len(chunks)} chunks)")
        embedded_chunks = batch_embed_chunks(chunks, max_tokens=self.config.chunking.max_tokens)

        if not embedded_chunks:
            self.logger.error(f"Embedding failed: {file_path.name}")
            self.stats.failed_files += 1
            self.stats.failed_list.append((str(file_path), "Embedding failed"))
            pbar.update(1)
            return

        # 6. Create Qdrant points with file hash
        points = []
        for i, chunk in enumerate(embedded_chunks):
            point = create_point(
                chunk=chunk,
                url=str(file_path),  # Using file path instead of URL
                title=metadata.get('title', file_path.name),
                chunk_index=i,
                total_chunks=len(embedded_chunks),
                file_hash=file_hash  # Add hash for deduplication
            )
            points.append(point)

        # 7. Upload to Qdrant
        pbar.set_postfix_str(f"Uploading: {file_path.name}")
        from lib.qdrant_operations import upload_points

        success = True
        for i in range(0, len(points), self.config.qdrant.batch_size):
            batch = points[i:i + self.config.qdrant.batch_size]
            if not upload_points(batch, collection_name=self.config.qdrant.collection):
                success = False
                break

        if success:
            self.stats.processed_files += 1
            self.stats.total_chunks += len(embedded_chunks)
            self.logger.info(f"✅ Processed: {file_path.name} ({len(embedded_chunks)} chunks)")
        else:
            self.stats.failed_files += 1
            self.stats.failed_list.append((str(file_path), "Upload failed"))
            self.logger.error(f"❌ Upload failed: {file_path.name}")

        pbar.update(1)

    def chunk_by_type(self, text: str, file_path: Path) -> List[Dict]:
        """
        Apply type-specific chunking strategy.

        Args:
            text: Cleaned text to chunk
            file_path: File path for determining type

        Returns:
            List of chunk dictionaries
        """
        # Determine chunking strategy based on file type
        extension = file_path.suffix.lower()
        strategies = self.config.chunking.strategies

        if extension in ['.md', '.markdown']:
            strategy = strategies.markdown
        elif extension in ['.py', '.js', '.java', '.cpp', '.go']:
            strategy = strategies.code
        elif extension == '.pdf':
            strategy = strategies.pdf
        else:
            strategy = strategies.default

        # For now, use semantic chunking for all
        # (type-specific implementations can be added later)
        self.logger.debug(f"Using {strategy} strategy for {file_path.name}")

        # Two-level chunking
        macro_chunks = semantic_chunk_text(
            text,
            chunk_size=self.config.chunking.chunk_size * 2,
            chunk_overlap=self.config.chunking.overlap
        )

        if not macro_chunks:
            return []

        fine_chunks = fine_chunk_text(
            macro_chunks,
            target_tokens=self.config.chunking.chunk_size,
            overlap_tokens=self.config.chunking.overlap
        )

        # Filter and validate chunks
        valid_chunks = filter_chunks(
            fine_chunks,
            min_tokens=50,
            max_tokens=self.config.chunking.max_tokens
        )

        return valid_chunks

    def generate_report(self) -> None:
        """Generate and save processing report."""
        duration = self.stats.duration()
        success_rate = self.stats.success_rate()

        if self.config.output.report_format == "markdown":
            report = f"""# Ragify Processing Report

## Summary
- **Date**: {datetime.now().isoformat()}
- **Duration**: {duration:.1f} seconds
- **Success Rate**: {success_rate:.1f}%

## Statistics
- **Total Files**: {self.stats.total_files}
- **Processed**: {self.stats.processed_files}
- **Skipped (unchanged)**: {self.stats.skipped_unchanged}
- **Failed**: {self.stats.failed_files}
- **Total Chunks Created**: {self.stats.total_chunks}
- **Total Data Processed**: {format_file_size(self.stats.total_bytes)}

## Average Metrics
- **Chunks per Document**: {self.stats.total_chunks / max(1, self.stats.processed_files):.1f}
- **Processing Speed**: {self.stats.total_files / max(1, duration):.1f} files/sec
"""

            if self.stats.failed_list:
                report += "\n## Failed Files\n"
                for file_path, error in self.stats.failed_list:
                    report += f"- `{file_path}`: {error}\n"

        elif self.config.output.report_format == "json":
            report_data = {
                "date": datetime.now().isoformat(),
                "duration": duration,
                "success_rate": success_rate,
                "stats": {
                    "total_files": self.stats.total_files,
                    "processed": self.stats.processed_files,
                    "skipped": self.stats.skipped_unchanged,
                    "failed": self.stats.failed_files,
                    "chunks": self.stats.total_chunks,
                    "bytes": self.stats.total_bytes
                },
                "failed": self.stats.failed_list
            }
            report = json.dumps(report_data, indent=2)

        else:
            report = f"Processing complete: {self.stats.processed_files}/{self.stats.total_files} files"

        # Save report
        with open(self.config.output.report_path, 'w') as f:
            f.write(report)

        self.logger.info(f"📊 Report saved to: {self.config.output.report_path}")

        # Also print summary to console
        print("\n" + "=" * 80)
        print("✨ RAGIFY PROCESSING COMPLETE")
        print("=" * 80)
        print(f"✅ Processed: {self.stats.processed_files}/{self.stats.total_files} files")
        print(f"⏭️  Skipped: {self.stats.skipped_unchanged} unchanged files")
        print(f"❌ Failed: {self.stats.failed_files} files")
        print(f"📦 Total chunks: {self.stats.total_chunks}")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📊 Report: {self.config.output.report_path}")
        print("=" * 80)


def main():
    """Main entry point for Ragify CLI."""
    parser = argparse.ArgumentParser(
        description='Ragify - Automated RAG Pipeline for Local Documentation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s index ./docs
  %(prog)s index ./docs --config custom.yaml
  %(prog)s index ./docs --chunk-size 600 --verbose
  %(prog)s init-config

Environment variables:
  OLLAMA_URL - Ollama API URL (default: http://localhost:11434)
  QDRANT_URL - Qdrant API URL (default: http://localhost:6333)
  QDRANT_API_KEY - Qdrant API key (optional)
"""
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Index command
    index_parser = subparsers.add_parser('index', help='Index documents from directory')
    index_parser.add_argument('directory', type=Path, help='Directory to index')
    index_parser.add_argument('--config', type=Path, help='Configuration file')
    index_parser.add_argument('--chunk-size', type=int, help='Override chunk size')
    index_parser.add_argument('--overlap', type=int, help='Override overlap')
    index_parser.add_argument('--batch-size', type=int, help='Override batch size')
    index_parser.add_argument('--collection', help='Override collection name')
    index_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    index_parser.add_argument('--no-tika', action='store_true', help='Skip Tika, process only text/code files')
    index_parser.add_argument('--non-interactive', action='store_true', help='Non-interactive mode (no prompts)')

    # Init config command
    init_parser = subparsers.add_parser('init-config', help='Create default configuration file')
    init_parser.add_argument('--path', type=Path, default='config.yaml', help='Config file path')

    # Query command
    query_parser = subparsers.add_parser('query', help='Query indexed documents')
    query_parser.add_argument('query', help='Search query text')
    query_parser.add_argument('--limit', type=int, default=5, help='Number of results (default: 5)')
    query_parser.add_argument('--collection', help='Collection name (default: documentation)')

    # List command
    list_parser = subparsers.add_parser('list', help='List indexed documents')
    list_parser.add_argument('--collection', help='Collection name (default: documentation)')

    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset (delete and recreate) collection')
    reset_parser.add_argument('--collection', help='Collection name (default: documentation)')
    reset_parser.add_argument('--all', action='store_true', dest='reset_all', help='Delete ALL collections (dangerous!)')
    reset_parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')

    # Doctor command
    doctor_parser = subparsers.add_parser('doctor', help='Check system prerequisites')
    doctor_parser.add_argument('--fix', action='store_true', help='Attempt to fix issues (install missing dependencies)')

    # Handle 'help' as alias for '-h' before parsing
    if len(sys.argv) > 1 and sys.argv[1] == 'help':
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Silent system check for all commands except doctor and init-config
    if args.command not in ['doctor', 'init-config']:
        from lib.doctor import run_silent_checks
        passed, failed_components = run_silent_checks()
        if not passed:
            print(f"❌ System check failed: {', '.join(failed_components)}")
            print(f"   Run 'python3 ragify.py doctor' for details and troubleshooting")
            sys.exit(1)

    if args.command == 'init-config':
        create_default_config(args.path)
        print(f"✅ Created default configuration at: {args.path}")
        sys.exit(0)

    if args.command == 'doctor':
        from lib.doctor import run_doctor_checks
        run_doctor_checks(fix=args.fix)
        sys.exit(0)

    if args.command == 'query':
        from lib.embedding import get_embedding

        # Load config to get collection name
        config_path = Path('config.yaml')
        if config_path.exists():
            config = RagifyConfig.load(config_path)
        else:
            config = RagifyConfig.default()
        collection = args.collection or config.qdrant.collection

        # Generate embedding for query
        print(f"🔍 Searching for: '{args.query}'")
        query_embedding = get_embedding(args.query, timeout=30, max_retries=1)

        if not query_embedding:
            print("❌ Failed to generate query embedding")
            print("   Make sure Ollama is running: ollama serve")
            sys.exit(1)

        # Search Qdrant
        if not QDRANT_CLIENT_AVAILABLE:
            print("❌ qdrant-client not available")
            sys.exit(1)

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models

            client = QdrantClient(
                url=config.qdrant.url,
                api_key=config.qdrant.api_key
            )

            results = client.query_points(
                collection_name=collection,
                query=query_embedding,
                limit=args.limit,
                with_payload=True
            ).points

            print(f"\n📊 Found {len(results)} results:\n")
            print("="*80)

            for i, result in enumerate(results, 1):
                score = result.score
                payload = result.payload
                print(f"\n[{i}] Score: {score:.4f}")
                print(f"Title: {payload.get('title', 'Unknown')}")
                print(f"File: {payload.get('url', 'Unknown')}")
                print(f"Chunks: {payload.get('chunk_index', 0)+1}/{payload.get('total_chunks', 1)}")
                print(f"\nContent:\n{payload.get('text', '')[:500]}...")
                print("-"*80)

        except Exception as e:
            print(f"❌ Query failed: {e}")
            sys.exit(1)

        sys.exit(0)

    if args.command == 'list':
        from collections import Counter

        # Load config to get collection name
        config_path = Path('config.yaml')
        if config_path.exists():
            config = RagifyConfig.load(config_path)
        else:
            config = RagifyConfig.default()
        collection = args.collection or config.qdrant.collection

        if not QDRANT_CLIENT_AVAILABLE:
            print("❌ qdrant-client not available")
            sys.exit(1)

        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(
                url=config.qdrant.url,
                api_key=config.qdrant.api_key
            )

            # Get collection info
            collection_info = client.get_collection(collection)

            print("="*80)
            print(f"📊 INDEXED DOCUMENTS - Collection '{collection}'")
            print("="*80)
            print(f"\n📦 General Statistics:")
            print(f"   Total chunks: {collection_info.points_count}")
            print(f"   Vector size: {collection_info.config.params.vectors.size}")

            # Scroll all points
            print(f"\n🔍 Loading documents...")

            urls_chunks = Counter()
            offset = None

            while True:
                results = client.scroll(
                    collection_name=collection,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )

                points, next_offset = results

                if not points:
                    break

                for point in points:
                    url = point.payload.get('url', 'N/A')
                    urls_chunks[url] += 1

                if next_offset is None:
                    break
                offset = next_offset

            # Display results
            print(f"\n📄 Unique documents: {len(urls_chunks)}")
            print("\n" + "="*80)
            print(f"{'#':<5} {'Chunks':<10} {'File'}")
            print("="*80)

            for i, (url, chunk_count) in enumerate(sorted(urls_chunks.items()), 1):
                # Shorten path for display
                display_path = str(Path(url).name) if len(url) > 60 else url
                print(f"{i:<5} {chunk_count:<10} {display_path}")

            print("="*80)
            print(f"\n✅ Total: {len(urls_chunks)} documents, {sum(urls_chunks.values())} chunks\n")

        except Exception as e:
            print(f"❌ List failed: {e}")
            sys.exit(1)

        sys.exit(0)

    if args.command == 'reset':
        if not QDRANT_CLIENT_AVAILABLE:
            print("❌ qdrant-client not available")
            sys.exit(1)

        from qdrant_client import QdrantClient
        from qdrant_client.http import models

        # Load config for API key
        config_path = Path('config.yaml')
        if config_path.exists():
            reset_config = RagifyConfig.load(config_path)
        else:
            reset_config = RagifyConfig.default()

        client = QdrantClient(
            url=reset_config.qdrant.url,
            api_key=reset_config.qdrant.api_key
        )

        # Handle --all flag: delete ALL collections
        if args.reset_all:
            print("\n" + "="*80)
            print("⚠️  RESET ALL QDRANT COLLECTIONS")
            print("="*80)

            try:
                collections = client.get_collections().collections
                if not collections:
                    print("\n⚠️  No collections found")
                    sys.exit(0)

                print(f"\nThis will DELETE ALL {len(collections)} collections:")
                for c in collections:
                    info = client.get_collection(c.name)
                    print(f"   - {c.name} ({info.points_count} points)")
                print("\nThis action CANNOT be undone!\n")

                if not args.confirm:
                    response = input("Type 'DELETE ALL' to confirm: ").strip()
                    if response != 'DELETE ALL':
                        print("❌ Reset cancelled")
                        sys.exit(0)

                for c in collections:
                    print(f"🗑️  Deleting '{c.name}'...")
                    client.delete_collection(c.name)

                print("\n" + "="*80)
                print(f"✅ DELETED {len(collections)} COLLECTIONS")
                print("="*80 + "\n")

            except Exception as e:
                print(f"❌ Reset failed: {e}")
                sys.exit(1)

            sys.exit(0)

        # Handle single collection reset
        config_path = Path('config.yaml')
        if config_path.exists():
            config = RagifyConfig.load(config_path)
        else:
            config = RagifyConfig.default()
        collection = args.collection or config.qdrant.collection

        print("\n" + "="*80)
        print("⚠️  RESET QDRANT COLLECTION")
        print("="*80)
        print(f"\nThis will DELETE all data in collection: '{collection}'")
        print("This action CANNOT be undone!\n")

        if not args.confirm:
            response = input("Type 'RESET' to confirm: ").strip()
            if response != 'RESET':
                print("❌ Reset cancelled")
                sys.exit(0)

        try:
            # Check if collection exists
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]

            if collection in collection_names:
                # Get info before deleting
                info = client.get_collection(collection)
                print(f"\n📊 Current state:")
                print(f"   Points: {info.points_count}")

                # Delete
                print(f"\n🗑️  Deleting collection '{collection}'...")
                client.delete_collection(collection)
                print(f"✅ Collection deleted")
            else:
                print(f"\n⚠️  Collection '{collection}' does not exist")

            # Recreate
            print(f"\n🔨 Creating collection '{collection}'...")
            client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(
                    size=768,  # nomic-embed-text
                    distance=models.Distance.COSINE
                )
            )
            print(f"✅ Collection created")
            print(f"   📏 Vector size: 768")
            print(f"   📐 Distance: Cosine")

            print("\n" + "="*80)
            print("✅ RESET COMPLETE")
            print("="*80 + "\n")

        except Exception as e:
            print(f"❌ Reset failed: {e}")
            sys.exit(1)

        sys.exit(0)

    if args.command == 'index':
        # Check Tika availability first
        from lib.tika_check import ensure_tika_ready

        use_tika = ensure_tika_ready(
            interactive=not args.non_interactive,
            auto_skip=args.no_tika
        )

        # Load configuration
        if args.config and args.config.exists():
            config = RagifyConfig.load(args.config)
        else:
            config = RagifyConfig.default()

        # Merge CLI arguments
        cli_args = {
            k: v for k, v in vars(args).items()
            if v is not None and k not in ['command', 'directory', 'config', 'no_tika', 'non_interactive']
        }
        config = merge_cli_args(config, cli_args)

        # Auto-derive collection name from folder if not specified
        if not args.collection:
            import re
            folder_name = args.directory.resolve().name
            # Sanitize: only alphanumeric and underscore, lowercase
            collection_name = re.sub(r'[^a-zA-Z0-9_]', '_', folder_name).lower()
            # Remove leading/trailing underscores and collapse multiple underscores
            collection_name = re.sub(r'_+', '_', collection_name).strip('_')
            # Ensure not empty
            if not collection_name:
                collection_name = 'documentation'
            config.qdrant.collection = collection_name
            print(f"📂 Collection auto-derivata dalla cartella: '{collection_name}'")

        # Verify connections
        if not check_qdrant_connection():
            print("❌ Cannot connect to Qdrant. Please ensure it's running.")
            sys.exit(1)

        # Check Ollama connection
        from lib.embedding import get_embedding

        test_embedding = get_embedding("test", timeout=5, max_retries=1)
        if test_embedding is None:
            print("❌ Cannot connect to Ollama. Please ensure it's running.")
            sys.exit(1)

        print("✅ All services connected successfully\n")

        # Run pipeline with Tika flag
        pipeline = RagifyPipeline(config, use_tika=use_tika)
        stats = pipeline.process_directory(args.directory)

        # Exit with appropriate code
        sys.exit(0 if stats['failed'] == 0 else 1)


if __name__ == "__main__":
    main()