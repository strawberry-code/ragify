#!/usr/bin/env python3
"""
Documentation Server - Serve local documentation files with HTML rendering
"""

import argparse
import os
import mimetypes
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse


class DocsHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler that:
    - Serves files from a specified directory
    - Generates directory listings as HTML
    - Serves markdown and text files as HTML
    """

    def __init__(self, *args, base_path=None, **kwargs):
        self.base_path = base_path or os.getcwd()
        super().__init__(*args, directory=self.base_path, **kwargs)

    def list_directory(self, path):
        """Generate a directory listing with proper HTML"""
        try:
            entries = os.listdir(path)
        except OSError:
            self.send_error(404, "Cannot list directory")
            return None

        entries.sort(key=lambda a: a.lower())

        # Get relative path from base
        rel_path = os.path.relpath(path, self.base_path)
        if rel_path == '.':
            rel_path = ''

        # Generate HTML
        html_parts = []
        html_parts.append('<!DOCTYPE html>')
        html_parts.append('<html><head>')
        html_parts.append('<meta charset="utf-8">')
        html_parts.append(f'<title>Index of /{rel_path}</title>')
        html_parts.append('<style>')
        html_parts.append('body { font-family: Arial, sans-serif; margin: 40px; }')
        html_parts.append('h1 { color: #333; }')
        html_parts.append('ul { list-style: none; padding: 0; }')
        html_parts.append('li { padding: 5px 0; }')
        html_parts.append('a { text-decoration: none; color: #0066cc; }')
        html_parts.append('a:hover { text-decoration: underline; }')
        html_parts.append('.dir { font-weight: bold; }')
        html_parts.append('.file { color: #333; }')
        html_parts.append('</style>')
        html_parts.append('</head><body>')
        html_parts.append(f'<h1>Index of /{rel_path}</h1>')
        html_parts.append('<hr>')
        html_parts.append('<ul>')

        # Add parent directory link
        if rel_path:
            parent = os.path.dirname(self.path)
            if not parent:
                parent = '/'
            html_parts.append(f'<li><a href="{parent}" class="dir">📁 ..</a></li>')

        # List directories first, then files
        dirs = []
        files = []

        for name in entries:
            if name.startswith('.'):
                continue

            fullname = os.path.join(path, name)
            linkname = urllib.parse.quote(name, errors='surrogatepass')

            if os.path.isdir(fullname):
                dirs.append((name, linkname))
            else:
                files.append((name, linkname))

        # Add directories
        for name, linkname in sorted(dirs):
            html_parts.append(f'<li><a href="{self.path}{linkname}/" class="dir">📁 {name}/</a></li>')

        # Add files
        for name, linkname in sorted(files):
            html_parts.append(f'<li><a href="{self.path}{linkname}" class="file">📄 {name}</a></li>')

        html_parts.append('</ul>')
        html_parts.append('<hr>')
        html_parts.append('</body></html>')

        content = '\n'.join(html_parts).encode('utf-8')

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()

        self.wfile.write(content)
        return None

    def guess_type(self, path):
        """Guess the MIME type, with special handling for documentation files"""
        base, ext = os.path.splitext(path)

        # Force markdown and text files to be served as HTML or plain text
        if ext.lower() in ['.md', '.markdown']:
            return 'text/plain'
        elif ext.lower() in ['.txt', '.rst']:
            return 'text/plain'
        elif ext.lower() in ['.html', '.htm']:
            return 'text/html'

        # Use default MIME type detection
        return super().guess_type(path)

    def end_headers(self):
        # Add CORS headers to allow crawler access
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()


def run_server(directory, port=8000):
    """
    Start the documentation server

    Args:
        directory: Directory to serve
        port: Port to listen on
    """
    # Convert to absolute path
    directory = os.path.abspath(directory)

    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory")
        return

    # Create handler with base path
    handler = lambda *args, **kwargs: DocsHTTPRequestHandler(
        *args, base_path=directory, **kwargs
    )

    server = HTTPServer(('0.0.0.0', port), handler)

    print(f"Documentation Server")
    print(f"=" * 80)
    print(f"Serving directory: {directory}")
    print(f"Server running at: http://localhost:{port}")
    print(f"Server running at: http://127.0.0.1:{port}")
    print(f"=" * 80)
    print(f"\nPress Ctrl+C to stop the server\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down server...")
        server.shutdown()
        print("Server stopped.")


def main():
    parser = argparse.ArgumentParser(
        description='Serve local documentation files with directory browsing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Serve current directory on port 8000
  python docs_server.py

  # Serve specific directory
  python docs_server.py /path/to/docs

  # Serve on custom port
  python docs_server.py /path/to/docs --port 8080

  # Once running, you can crawl with:
  python url_crawler.py http://localhost:8000 --output urls.txt
        """
    )
    parser.add_argument('directory', nargs='?', default='.',
                       help='Directory to serve (default: current directory)')
    parser.add_argument('--port', type=int, default=8000,
                       help='Port to listen on (default: 8000)')

    args = parser.parse_args()

    run_server(args.directory, args.port)


if __name__ == '__main__':
    main()
