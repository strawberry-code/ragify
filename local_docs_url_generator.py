#!/usr/bin/env python3
"""
Local Documentation URL Generator - Generate URLs from local filesystem
"""

import argparse
import os
from pathlib import Path
from urllib.parse import quote


def generate_urls(directory_path, base_url="http://localhost:8000", output_file=None):
    """
    Generate URLs from all files in a directory recursively

    Args:
        directory_path: Path to the directory containing documentation
        base_url: Base URL of the local server
        output_file: Optional output file path

    Returns:
        List of generated URLs
    """
    # Validate directory exists
    if not os.path.isdir(directory_path):
        raise ValueError(f"Error: '{directory_path}' is not a valid directory")

    # Convert to absolute path
    abs_directory = os.path.abspath(directory_path)

    # Find all files recursively
    all_files = []
    print(f"Scanning directory: {abs_directory}")
    print("-" * 80)

    # Use os.walk to get all files recursively
    for root, dirs, files in os.walk(abs_directory):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            # Skip hidden files
            if file.startswith('.'):
                continue

            # Skip common non-documentation files and images
            skip_extensions = [
                '.pyc', '.pyo', '.so', '.dylib', '.dll', '.exe',  # Binary/compiled
                '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.ico', '.webp'  # Images
            ]
            if any(file.lower().endswith(ext) for ext in skip_extensions):
                continue

            # Get absolute path
            abs_file_path = os.path.join(root, file)
            all_files.append(abs_file_path)

    print(f"Found {len(all_files)} files\n")

    # Generate URLs
    urls = []
    for file_path in sorted(all_files):
        # Get relative path from base directory
        rel_path = os.path.relpath(file_path, abs_directory)

        # URL encode the path components
        path_parts = rel_path.split(os.sep)
        encoded_parts = [quote(part, safe='') for part in path_parts]
        url_path = '/'.join(encoded_parts)

        # Construct full URL
        full_url = f"{base_url.rstrip('/')}/{url_path}"
        urls.append(full_url)

    # Print results
    print("=" * 80)
    print(f"Generated {len(urls)} URLs")
    print("=" * 80)
    print("\nURLs:")
    for url in urls:
        print(url)

    # Save to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            f.write('\n'.join(urls))
        print(f"\nURLs saved to: {output_file}")

    return urls


def main():
    parser = argparse.ArgumentParser(
        description='Generate URLs from local documentation files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate URLs from a directory
  python local_docs_url_generator.py /path/to/docs

  # Generate URLs with custom base URL
  python local_docs_url_generator.py /path/to/docs --base-url http://localhost:9000

  # Save to file
  python local_docs_url_generator.py /path/to/docs --output urls.txt

  # Complete workflow:
  # 1. Generate URLs from local directory
  python local_docs_url_generator.py /path/to/docs --output urls.txt

  # 2. Start the docs server on that directory
  python docs_server.py /path/to/docs --port 8000

  # 3. Use the URLs with ragdocs in Crush
        """
    )
    parser.add_argument('directory',
                       help='Path to directory containing documentation (REQUIRED)')
    parser.add_argument('--base-url', default='http://localhost:8000',
                       help='Base URL of the local server (default: http://localhost:8000)')
    parser.add_argument('--output', '-o',
                       help='Output file to save URLs (optional)')

    args = parser.parse_args()

    try:
        generate_urls(args.directory, args.base_url, args.output)
    except ValueError as e:
        print(f"\n{e}")
        parser.print_help()
        exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        exit(1)


if __name__ == '__main__':
    main()
