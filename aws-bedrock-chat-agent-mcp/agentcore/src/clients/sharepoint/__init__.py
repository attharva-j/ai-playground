"""SharePoint integration for AgentCore MCP Server."""

from clients.sharepoint.auth import (
    SharePointContext,
    get_sharepoint_auth_context,
    get_access_token_decorator,
)
from clients.sharepoint.graph_client import GraphClient

__all__ = [
    "SharePointContext",
    "get_sharepoint_auth_context",
    "get_access_token_decorator",
    "GraphClient",
]