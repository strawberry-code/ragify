#!/usr/bin/env python3
"""
Script per aggiungere documentazione da URL a Qdrant con semantic chunking.
Legge URL da un file (una per riga) e li indicizza usando Chonkie + semchunk.

Pipeline:
1. Download HTML
2. Extract text
3. Clean text (unicode, whitespace, boilerplate)
4. Semantic chunking (Chonkie → macro-blocks)
5. Fine chunking (semchunk → embedding-ready chunks)
6. Embedding (Ollama nomic-embed-text)
7. Upload to Qdrant

Usage:
    python3 add_urls_to_qdrant.py <file_urls.txt> [--chunk-size 500] [--verbose]
"""

import sys
import logging
import argparse
from pathlib import Path

# Import local library modules
from lib import (
    clean_text,
    validate_text_quality,
    semantic_chunk_text,
    fine_chunk_text,
    filter_chunks,
    batch_embed_chunks,
    batch_upload_chunks,
    check_qdrant_connection
)

# BeautifulSoup for HTML parsing
import requests
from bs4 import BeautifulSoup


# Configuration
DEFAULT_CHUNK_SIZE = 500  # tokens
DEFAULT_OVERLAP = 50  # tokens
MAX_TOKENS = 8192  # nomic-embed-text limit


def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )


def fetch_url_content(url: str) -> tuple[str, str] | tuple[None, None]:
    """
    Download and extract text from URL.
    
    Args:
        url: URL to fetch
        
    Returns:
        (text, title) tuple or (None, None) if failed
    """
    try:
        logging.info(f"📥 Downloading: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe']):
            element.decompose()
        
        # Extract text
        text = soup.get_text(separator='\n', strip=True)
        
        # Extract title
        title = soup.find('title')
        title_text = title.get_text().strip() if title else url
        
        logging.info(f"📄 Title: {title_text}")
        logging.info(f"📏 Raw length: {len(text)} characters")
        
        return text, title_text
        
    except Exception as e:
        logging.error(f"❌ Download failed: {e}")
        return None, None


def process_url(
    url: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP
) -> dict:
    """
    Process a single URL through the complete pipeline.
    
    Args:
        url: URL to process
        chunk_size: Target chunk size in tokens
        overlap: Overlap between chunks in tokens
        
    Returns:
        Statistics dictionary
    """
    stats = {
        'url': url,
        'success': False,
        'raw_chars': 0,
        'clean_chars': 0,
        'macro_chunks': 0,
        'final_chunks': 0,
        'uploaded_chunks': 0,
        'errors': []
    }
    
    # 1. Download
    raw_text, title = fetch_url_content(url)
    if raw_text is None:
        stats['errors'].append('Download failed')
        return stats
    
    stats['raw_chars'] = len(raw_text)
    
    # 2. Clean text
    logging.info("🧹 Cleaning text...")
    cleaned_text = clean_text(raw_text)
    stats['clean_chars'] = len(cleaned_text)
    
    # Validate quality
    if not validate_text_quality(cleaned_text, min_length=100):
        logging.warning("⚠️  Text quality too low, skipping")
        stats['errors'].append('Text quality too low')
        return stats
    
    logging.info(f"✓ Cleaned: {stats['clean_chars']} chars ({stats['raw_chars'] - stats['clean_chars']} removed)")
    
    # 3. Semantic chunking (Chonkie)
    logging.info("✂️  Semantic chunking (Chonkie)...")
    macro_chunks = semantic_chunk_text(cleaned_text, chunk_size=chunk_size * 2, chunk_overlap=overlap)
    stats['macro_chunks'] = len(macro_chunks)
    logging.info(f"✓ Created {stats['macro_chunks']} macro-semantic blocks")
    
    # 4. Fine chunking (semchunk)
    logging.info("🔬 Fine chunking (semchunk)...")
    fine_chunks = fine_chunk_text(macro_chunks, target_tokens=chunk_size, overlap_tokens=overlap)
    logging.info(f"✓ Created {len(fine_chunks)} fine chunks")
    
    # 5. Filter chunks
    logging.info("🔍 Filtering chunks...")
    valid_chunks = filter_chunks(fine_chunks, min_tokens=50, max_tokens=MAX_TOKENS)
    stats['final_chunks'] = len(valid_chunks)
    
    if stats['final_chunks'] == 0:
        logging.warning("⚠️  No valid chunks after filtering")
        stats['errors'].append('No valid chunks')
        return stats
    
    # Calculate statistics
    token_counts = [c['token_count'] for c in valid_chunks]
    avg_tokens = sum(token_counts) / len(token_counts)
    min_tokens = min(token_counts)
    max_tokens_actual = max(token_counts)
    
    logging.info(f"📊 Chunk stats: avg={avg_tokens:.0f}, min={min_tokens}, max={max_tokens_actual} tokens")
    
    # 6. Embedding
    logging.info(f"🤖 Generating embeddings ({len(valid_chunks)} chunks)...")
    embedded_chunks = batch_embed_chunks(valid_chunks, max_tokens=MAX_TOKENS)
    
    if len(embedded_chunks) == 0:
        logging.error("❌ All embeddings failed")
        stats['errors'].append('Embedding failed')
        return stats
    
    logging.info(f"✓ Embedded {len(embedded_chunks)} chunks")
    
    # 7. Upload to Qdrant
    logging.info("📤 Uploading to Qdrant...")
    uploaded = batch_upload_chunks(embedded_chunks, url, title)
    stats['uploaded_chunks'] = uploaded
    
    if uploaded > 0:
        stats['success'] = True
        logging.info(f"✅ Successfully uploaded {uploaded} chunks for: {title}")
    else:
        logging.error("❌ Upload failed")
        stats['errors'].append('Upload failed')
    
    return stats


def process_urls_file(
    filename: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP
):
    """
    Process all URLs from a file.
    
    Args:
        filename: Path to file with URLs (one per line)
        chunk_size: Target chunk size in tokens
        overlap: Overlap between chunks in tokens
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        logging.info(f"📋 Found {len(urls)} URLs to process\n")
        
        all_stats = []
        successful = 0
        failed = 0
        total_chunks = 0
        failed_urls = []
        
        for i, url in enumerate(urls, 1):
            print(f"\n{'='*80}")
            logging.info(f"[{i}/{len(urls)}] Processing: {url}")
            print(f"{'='*80}\n")
            
            stats = process_url(url, chunk_size, overlap)
            all_stats.append(stats)
            
            if stats['success']:
                successful += 1
                total_chunks += stats['uploaded_chunks']
            else:
                failed += 1
                failed_urls.append(url)
                logging.error(f"❌ Failed: {', '.join(stats['errors'])}")
        
        # Save failed URLs to file
        failed_file = None
        if failed_urls:
            failed_file = Path(filename).parent / "failed_uploaded_urls.txt"
            with open(failed_file, 'w', encoding='utf-8') as f:
                for url in failed_urls:
                    f.write(f"{url}\n")
            logging.info(f"💾 Failed URLs saved to: {failed_file.absolute()}")
        
        # Final report
        print(f"\n{'='*80}")
        print("✨ PROCESSING COMPLETE")
        print(f"{'='*80}")
        print(f"✅ Successful: {successful}/{len(urls)} URLs")
        print(f"❌ Failed: {failed}/{len(urls)} URLs")
        if failed_file:
            print(f"📝 Failed URLs saved to: {failed_file.absolute()}")
        print(f"📦 Total chunks uploaded: {total_chunks}")
        
        # Detailed stats
        if successful > 0:
            avg_chunks = total_chunks / successful
            print(f"📊 Average chunks per document: {avg_chunks:.1f}")
        
        print(f"{'='*80}\n")
        
    except FileNotFoundError:
        logging.error(f"❌ File not found: {filename}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"❌ Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Add URLs to Qdrant with semantic chunking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s urls.txt
  %(prog)s urls.txt --chunk-size 600 --overlap 60
  %(prog)s urls.txt --verbose

File format (urls.txt):
  https://example.com/doc1
  https://example.com/doc2
  # Comments are ignored
        """
    )
    
    parser.add_argument('urls_file', help='File containing URLs (one per line)')
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f'Target chunk size in tokens (default: {DEFAULT_CHUNK_SIZE})'
    )
    parser.add_argument(
        '--overlap',
        type=int,
        default=DEFAULT_OVERLAP,
        help=f'Overlap between chunks in tokens (default: {DEFAULT_OVERLAP})'
    )
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=MAX_TOKENS,
        help=f'Maximum tokens per chunk (default: {MAX_TOKENS})'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Print configuration
    logging.info("🚀 RAG Document Indexer with Semantic Chunking")
    logging.info(f"📁 URLs file: {args.urls_file}")
    logging.info(f"✂️  Chunk size: {args.chunk_size} tokens (overlap: {args.overlap})")
    logging.info(f"🤖 Embedding model: nomic-embed-text via Ollama")
    logging.info(f"🗄️  Collection: documentation")
    
    # Check Qdrant connection
    if not check_qdrant_connection():
        logging.error("❌ Cannot connect to Qdrant")
        sys.exit(1)
    logging.info("✅ Qdrant connected\n")
    
    # Process URLs
    process_urls_file(args.urls_file, args.chunk_size, args.overlap)


if __name__ == "__main__":
    main()
