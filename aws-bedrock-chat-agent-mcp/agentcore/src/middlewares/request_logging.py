# middleware.py
import logging
import time
from typing import Callable
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("mcp_image_generator")

MCP_SESSION_HEADER = "mcp-session-id"

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        start = time.time()

        # Log immediately so you see hits even if handler hangs
        try:
            body = await request.body()
            method = None
            if body:
                try:
                    payload = json.loads(body.decode("utf-8", errors="replace"))
                    method = payload.get("method")
                except Exception:
                    logger.warning("Could not parse JSON-RPC body: %s", str(e))
                    method = None
        except Exception:
            method = None

        logger.warning("MCP_HTTP_IN %s %s rpc_method=%s", request.method, request.url.path, method)

        resp: Response = await call_next(request)
        dt_ms = int((time.time() - start) * 1000)
        logger.warning("MCP_HTTP_OUT %s %s status=%s latency_ms=%s", request.method, request.url.path, resp.status_code, dt_ms)
        return resp
