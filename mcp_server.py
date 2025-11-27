#!/usr/bin/env python3
"""
Entry point per server MCP Ragify.

Questo server MCP espone tool per interrogare la documentazione
indicizzata in Qdrant usando ricerca semantica.

Uso:
    python mcp_server.py                 # Avvia server (stdio)
    mcp dev mcp_server.py               # Dev con MCP Inspector
    mcp install mcp_server.py           # Installa per Claude Desktop

Tools esposti:
    - search_documentation: Ricerca semantica nella documentazione
    - list_collections: Elenca le collection disponibili
    - list_sources: Elenca i file in una collection
"""

from lib.mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
