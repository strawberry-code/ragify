"""
MCP SSE Transport routes.

Implements Server-Sent Events transport for MCP protocol,
allowing Claude Desktop and other clients to connect via HTTP.
"""

import os
import json
import asyncio
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

# Import MCP tools logic
from qdrant_client import QdrantClient
import requests

router = APIRouter()

# Configuration
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')

# Active SSE connections
connections: dict[str, asyncio.Queue] = {}


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client."""
    if QDRANT_API_KEY:
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return QdrantClient(url=QDRANT_URL)


def get_embedding(text: str, model: str = "nomic-embed-text") -> list[float] | None:
    """Generate embedding using Ollama."""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("embedding")
    except Exception:
        return None


# MCP Tool implementations
def search_documentation(query: str, collection: str = "documentation", limit: int = 5) -> str:
    """Search documentation with semantic search."""
    try:
        client = get_qdrant_client()

        # Check collection exists
        try:
            client.get_collection(collection)
        except Exception:
            return f"Collection '{collection}' not found"

        # Generate embedding
        embedding = get_embedding(query)
        if not embedding:
            return "Failed to generate embedding. Is Ollama running with nomic-embed-text?"

        # Search
        results = client.query_points(
            collection_name=collection,
            query=embedding,
            limit=limit,
            with_payload=True
        )

        if not results.points:
            return f"No results found for: {query}"

        # Format results
        output = []
        for i, point in enumerate(results.points, 1):
            score = point.score
            payload = point.payload
            text = payload.get("text", "")[:500]
            url = payload.get("url", "unknown")
            title = payload.get("title", "Untitled")

            output.append(f"[{i}] Score: {score:.3f}\nFile: {url}\nTitle: {title}\n{text}\n")

        return "\n---\n".join(output)
    except Exception as e:
        return f"Search error: {str(e)}"


def list_collections() -> str:
    """List all Qdrant collections."""
    try:
        client = get_qdrant_client()
        collections = client.get_collections()

        if not collections.collections:
            return "No collections found"

        output = []
        for coll in collections.collections:
            info = client.get_collection(coll.name)
            output.append(f"- {coll.name}: {info.points_count} points")

        return "\n".join(output)
    except Exception as e:
        return f"Error listing collections: {str(e)}"


def list_sources(collection: str = "documentation") -> str:
    """List indexed sources in a collection."""
    try:
        client = get_qdrant_client()

        sources = {}
        offset = None

        while True:
            results, offset = client.scroll(
                collection_name=collection,
                limit=1000,
                offset=offset,
                with_payload=["url"],
                with_vectors=False
            )

            for point in results:
                url = point.payload.get("url", "unknown")
                sources[url] = sources.get(url, 0) + 1

            if offset is None:
                break

        if not sources:
            return f"No sources in collection '{collection}'"

        output = [f"Sources in '{collection}':"]
        for url, count in sorted(sources.items()):
            short_url = url if len(url) <= 60 else f"...{url[-57:]}"
            output.append(f"- {short_url}: {count} chunks")

        output.append(f"\nTotal: {len(sources)} files, {sum(sources.values())} chunks")
        return "\n".join(output)
    except Exception as e:
        return f"Error listing sources: {str(e)}"


# MCP Protocol handlers
MCP_TOOLS = {
    "search_documentation": {
        "description": "Search documentation using semantic search",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "collection": {"type": "string", "default": "documentation"},
                "limit": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        },
        "handler": search_documentation
    },
    "list_collections": {
        "description": "List all available collections",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": list_collections
    },
    "list_sources": {
        "description": "List indexed sources in a collection",
        "inputSchema": {
            "type": "object",
            "properties": {
                "collection": {"type": "string", "default": "documentation"}
            }
        },
        "handler": list_sources
    }
}


def handle_mcp_message(message: dict) -> dict:
    """
    Handle MCP JSON-RPC message.

    Args:
        message: JSON-RPC request

    Returns:
        dict: JSON-RPC response
    """
    method = message.get("method", "")
    msg_id = message.get("id")
    params = message.get("params", {})

    # Initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "ragify",
                    "version": "1.0.0"
                }
            }
        }

    # List tools
    if method == "tools/list":
        tools = []
        for name, tool in MCP_TOOLS.items():
            tools.append({
                "name": name,
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            })
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": tools}
        }

    # Call tool
    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        if tool_name not in MCP_TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }

        try:
            result = MCP_TOOLS[tool_name]["handler"](**tool_args)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": result}]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32000,
                    "message": str(e)
                }
            }

    # Unknown method
    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }


class MCPMessage(BaseModel):
    """MCP message request body."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[dict] = None
    id: Optional[int | str] = None


@router.get("/sse")
async def mcp_sse(request: Request):
    """
    SSE endpoint for MCP communication.

    Clients connect here to receive server-sent events.
    Messages are sent via POST to /mcp/message.
    """
    connection_id = str(uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    connections[connection_id] = queue

    async def event_generator():
        try:
            # Send connection ID as first event
            yield {
                "event": "connection",
                "data": json.dumps({"connection_id": connection_id})
            }

            # Keep connection alive and send messages
            while True:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(queue.get(), timeout=30)
                    yield {
                        "event": "message",
                        "data": json.dumps(message)
                    }
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "ping", "data": ""}

        except asyncio.CancelledError:
            pass
        finally:
            connections.pop(connection_id, None)

    return EventSourceResponse(event_generator())


@router.post("/message")
async def mcp_message(request: Request, message: MCPMessage, connection_id: Optional[str] = None):
    """
    Send message to MCP server.

    Args:
        message: MCP JSON-RPC message
        connection_id: SSE connection ID (optional)

    Returns:
        dict: MCP response
    """
    # Handle message
    response = handle_mcp_message(message.model_dump())

    # If connection_id provided, also send via SSE
    if connection_id and connection_id in connections:
        await connections[connection_id].put(response)

    return response


@router.get("/tools")
async def list_mcp_tools():
    """
    List available MCP tools.

    Returns:
        dict: List of tools with schemas
    """
    tools = []
    for name, tool in MCP_TOOLS.items():
        tools.append({
            "name": name,
            "description": tool["description"],
            "inputSchema": tool["inputSchema"]
        })
    return {"tools": tools}
