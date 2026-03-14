"""SharePoint authentication handler for AgentCore MCP Server using AWS Credential Provider."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Any

from bedrock_agentcore.identity.auth import requires_access_token

logger = logging.getLogger("sharepoint_auth")


@dataclass
class SharePointContext:
    """Context object for SharePoint connection using AWS Credential Provider."""
    
    provider_name: str
    scopes: list[str]
    auth_flow: str
    callback_url: str
    graph_url: str = "https://graph.microsoft.com/v1.0"
    
    def get_headers(self, access_token: str) -> Dict[str, str]:
        """
        Get authorization headers for Microsoft Graph API calls.
        
        Args:
            access_token: OAuth2 access token from credential provider
            
        Returns:
            Headers dictionary with authorization
        """
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }


# --- DROP-IN REPLACEMENT: get_sharepoint_auth_context ---

async def get_sharepoint_auth_context(secrets: Dict[str, Any]) -> SharePointContext:
    """
    Build SharePoint auth context for AgentCore Identity.
    """

    provider_name = (secrets.get("SHAREPOINT_PROVIDER_NAME") or "microsoft-oauth-provider").strip()
    callback_url = (secrets.get("SHAREPOINT_CALLBACK_URL") or "").strip()
    auth_flow = (secrets.get("SHAREPOINT_AUTH_FLOW") or "M2M").strip().upper()

    # Defaults:
    # - USER_FEDERATION: delegated scopes (v2 format) + OIDC scopes (recommended)
    # - M2M: .default
    default_scopes_user = [
        "openid",
        "profile",
        "offline_access",
        "Sites.Read.All",
        "Files.Read.All",
    ]
    default_scopes_m2m = ["https://graph.microsoft.com/.default"]

    scopes_str = (secrets.get("SHAREPOINT_SCOPES") or "").strip()
    if scopes_str:
        scopes = [s.strip() for s in scopes_str.split(",") if s.strip()]
    else:
        scopes = default_scopes_m2m if auth_flow == "M2M" else default_scopes_user

    # Callback URL required only for USER_FEDERATION (session binding)
    if auth_flow != "M2M" and not callback_url:
        raise ValueError(
            "SHAREPOINT_CALLBACK_URL is required for USER_FEDERATION OAuth2 session binding. "
            "Use the callback URL shown on the AgentCore Identity provider details page."
        )

    logger.info("SharePoint auth context initialized with provider=%s auth_flow=%s scopes=%s",
                provider_name, auth_flow, ",".join(scopes))

    return SharePointContext(
        provider_name=provider_name,
        scopes=scopes,
        auth_flow=auth_flow,
        callback_url=callback_url,
    )

"""
    Get the @requires_access_token decorator configured for SharePoint.
    
    This decorator should be applied to functions that need SharePoint access tokens.
    
    Args:
        context: SharePoint authentication context
        force_auth: Whether to force re-authentication
        
    Returns:
        Configured @requires_access_token decorator
        
    Example:
        @get_access_token_decorator(sharepoint_context)
        async def my_sharepoint_function(*, access_token: str):
            # Use access_token to call Microsoft Graph API
            pass
    """
def get_access_token_decorator(
    context: SharePointContext,
    force_auth: bool = False,
    on_auth_url=None,
):
    """
    Get the @requires_access_token decorator configured for SharePoint.
    
    This decorator should be applied to functions that need SharePoint access tokens.
    
    Args:
        context: SharePoint authentication context
        force_auth: Whether to force re-authentication
        
    Returns:
        Configured @requires_access_token decorator
        
    Example:
        @get_access_token_decorator(sharepoint_context)
        async def my_sharepoint_function(*, access_token: str):
            # Use access_token to call Microsoft Graph API
            pass

    IMPORTANT:
    - Uses caller-supplied on_auth_url when provided (so tools can return auth URL).
    - Only passes callback_url when needed (USER_FEDERATION).
    """
    kwargs = dict(
        provider_name=context.provider_name,
        scopes=context.scopes,
        auth_flow=context.auth_flow,
        force_authentication=force_auth,
        on_auth_url=on_auth_url or (lambda url: logger.info("Authorization URL: %s", url)),
    )

    # callback_url is relevant for USER_FEDERATION; safe to omit for M2M.
    if context.auth_flow != "M2M":
        kwargs["callback_url"] = context.callback_url

    return requires_access_token(**kwargs)