"""
FastMCP Server (stateless HTTP + process-level cached context)
- stateless_http=True => lifespan runs per request
- cache AppContext at module level to avoid re-initializing AWS clients each request
- bind host/port via FastMCP Settings env vars (FASTMCP_HOST / FASTMCP_PORT)
  (we map HOST/PORT -> FASTMCP_HOST/FASTMCP_PORT if provided)
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any, Dict

import boto3

from fastmcp import FastMCP, Context
from fastmcp.server.http import create_streamable_http_app

from clients.secrets_client import get_secret
from utils.logger_util import setup_logger

from clients.bedrock_client import BedrockClient
from clients.guardrail_client import GuardrailClient
from clients.s3_client import S3Client
from clients.sharepoint import get_sharepoint_auth_context, SharePointContext, GraphClient

from starlette.middleware import Middleware
from middlewares.request_logging import RequestLoggingMiddleware
from fastmcp.server.http import create_streamable_http_app

from mcp_tools.image_tools import register_image_tools
from mcp_tools.sharepoint_tools import register_sharepoint_tools

logger = logging.getLogger("agentcore_mcp_server")

SECRETS = get_secret()


@dataclass
class AppContext:
    """
    Shared context available to ALL tools via:
    ctx.request_context.lifespan_context
    """
    secrets: Dict[str, Any]
    bedrock: BedrockClient
    guardrail: GuardrailClient
    s3: S3Client
    audit_table: Any  # DynamoDB Table or None
    ddb: Any          # boto3 resource or None
    sharepoint_context: SharePointContext | None  # SharePoint auth context
    graph_client: GraphClient | None  # Microsoft Graph API client


# ----------------------------
# Process-level singleton cache
# ----------------------------
_APP_CTX: AppContext | None = None
_LOGGER_CONFIGURED: bool = False


def _init_audit_table(secrets: Dict[str, Any]):
    table_name = secrets.get("DDB_AUDIT_TABLE")
    if not table_name:
        return None, None
    ddb = boto3.resource("dynamodb", region_name=secrets["AWS_REGION"])
    return ddb, ddb.Table(table_name)


async def _build_app_context() -> AppContext:
    """
    Builds the AppContext once per process.
    """
    global _LOGGER_CONFIGURED
    global SECRETS

    secrets = SECRETS

    # Configure logger once per process (avoid duplicate handlers)
    if not _LOGGER_CONFIGURED:
        setup_logger(
            secrets.get("LOG_LEVEL", "INFO").upper(),
            secrets.get("ENABLE_CLOUDWATCH_LOGS", "false").lower(),
        )
        _LOGGER_CONFIGURED = True

    logger.info("Initializing AppContext (process singleton)...")

    # Initialize AWS clients
    bedrock = BedrockClient(secrets["AWS_REGION"], secrets)
    guardrail = GuardrailClient(
        secrets["AWS_REGION"],
        secrets["GUARDRAIL_ID"],
        secrets["GUARDRAIL_VERSION"],
    )
    s3 = S3Client(
        secrets["AWS_REGION"],
        secrets["S3_BUCKET"],
        int(secrets["PRESIGNED_URL_EXPIRY"]),
    )

    ddb, audit_table = _init_audit_table(secrets)

    # Initialize SharePoint clients (optional - only if configured)
    sharepoint_context = None
    graph_client = None
    
    try:
        # Check if SharePoint Credential Provider is configured
        provider_name = secrets.get("SHAREPOINT_PROVIDER_NAME", "microsoft-oauth-provider")
        callback_url = (secrets.get("SHAREPOINT_CALLBACK_URL") or "").strip()
        auth_flow = (secrets.get("SHAREPOINT_AUTH_FLOW") or "USER_FEDERATION").strip().upper()

        if auth_flow == "M2M" or callback_url:
            logger.info("SharePoint config detected (auth_flow=%s). Initializing SharePoint context...", auth_flow)
            sharepoint_context = await get_sharepoint_auth_context(secrets)
            graph_client = GraphClient(sharepoint_context)
            logger.info("SharePoint context initialized with provider: %s", provider_name)
        else:
            logger.info("SharePoint not configured (missing SHAREPOINT_CALLBACK_URL for USER_FEDERATION), skipping SharePoint initialization")
    except Exception as e:
        logger.warning(f"Failed to initialize SharePoint context: {str(e)}")
        logger.warning("SharePoint tools will not be available")

    return AppContext(
        secrets=secrets,
        bedrock=bedrock,
        guardrail=guardrail,
        s3=s3,
        audit_table=audit_table,
        ddb=ddb,
        sharepoint_context=sharepoint_context,
        graph_client=graph_client,
    )


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """
    Stateless HTTP mode => this lifespan is entered/exited per request.
    We return a cached, process-singleton AppContext to avoid recreating AWS clients.
    """
    global _APP_CTX

    if _APP_CTX is None:
        _APP_CTX = await _build_app_context()

    yield _APP_CTX


# ---- FastMCP server object (CLI/deployer-friendly) ----
APP_NAME = "agentcore-mcp-tools"

mcp = FastMCP(
    APP_NAME,
    # host=SECRETS["HOST"],
    lifespan=app_lifespan,
    # stateless_http=True,  # option B requires this stays true
)


# ============================================================
# 🔹 HELLO TOOL (Health / Context Check)
# ============================================================

@mcp.tool()
async def hello(ctx: Context, name: str = "world") -> Dict[str, Any]:
    """
    Simple hello tool to verify:
    - Lifespan context injection
    - Singleton AppContext reuse
    - Tool invocation path (not protocol PingRequest)
    """
    app_ctx = ctx.request_context.lifespan_context
    if app_ctx is None:
        raise RuntimeError("AppContext not available")

    logger.info("HELLO TOOL HIT name=%s app_context_id=%s", name, id(app_ctx))

    return {
        "message": f"Hello, {name}!",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app_context_id": id(app_ctx),
        "region": app_ctx.secrets.get("AWS_REGION"),
        "singleton_working": True,
    }


# ---- register all tools here ----
register_image_tools(mcp)
register_sharepoint_tools(mcp)

# ✅ This is the correct ASGI app for uvicorn (fastmcp)
# IMPORTANT: AgentCore requires POST /mcp and stateless streamable-http
app = create_streamable_http_app(
    server=mcp,
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
    debug=True,
    middleware=[Middleware(RequestLoggingMiddleware)],
)


def main():
    logger.info("Starting FastMCP server...")
    # Run the server with streamable HTTP transport
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
