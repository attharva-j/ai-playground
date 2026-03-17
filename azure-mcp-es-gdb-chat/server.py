import os
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.middleware.wsgi import WSGIMiddleware
import uvicorn

from mcp_app import create_server, create_app

# Instances
mcp = create_server()
flask_app = create_app()

def build_mcp_apps(mcp_server):
    """
    Prefer the modern HTTP APIs (FastMCP >= 2.3.2).
    Fallback to the deprecated methods if we're on an older version.
    """
    try:
        # New, non-deprecated API
        from fastmcp.server import http as mcp_http
        sse_app = mcp_http.create_sse_app(mcp_server)   
        http_app = mcp_http.http_app(mcp_server)  
        return sse_app, http_app
    except Exception:
        return mcp_server.sse_app(), mcp_server.streamable_http_app()

sse_endpoint, http_endpoint = build_mcp_apps(mcp)

# Main ASGI app: mount MCP endpoints and (optionally) Flask at root
app = Starlette(routes=[
    Mount("/mcp", app=sse_endpoint),   # SSE endpoint
    Mount("/sse", app=http_endpoint),  # non-SSE HTTP endpoint
    Mount("/", app=WSGIMiddleware(flask_app)),  
],
lifespan=http_endpoint.lifespan)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)