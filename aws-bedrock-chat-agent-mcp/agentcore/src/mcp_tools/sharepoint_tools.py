from __future__ import annotations

import logging
from typing import Any, Dict

from fastmcp import FastMCP, Context

from clients.sharepoint.auth import get_access_token_decorator
from utils.document_processor import DocumentProcessor

from urllib.parse import urlparse
from typing import Tuple

logger = logging.getLogger("mcp_sharepoint_tools")


def _ctx(ctx: Context):
    """
    AppContext injected by lifespan() in main.py
    """
    app_ctx = ctx.request_context.lifespan_context
    if app_ctx is None:
        raise RuntimeError(
            "Missing lifespan context. Ensure FastMCP server uses lifespan=app_lifespan "
            "and that requests are routed through the FastMCP server instance."
        )
    return app_ctx

def _parse_site_url(site_url: str) -> Tuple[str, str]:
    """
    Returns (domain, site_path) from SHAREPOINT_SITE_URL.
    Examples:
      https://teams.<your-domain.com>/sites/aifactory -> (teams.<your-domain.com>, /sites/aifactory)
      teams.<your-domain.com>/sites/aifactory        -> (teams.<your-domain.com>, /sites/aifactory)
      https://teams.<your-domain.com>                -> (teams.<your-domain.com>, /)
    """
    raw = (site_url or "").strip()
    if not raw:
        raise ValueError("SHAREPOINT_SITE_URL not configured")

    if "://" not in raw:
        raw = "https://" + raw

    u = urlparse(raw)
    domain = u.netloc
    if not domain:
        raise ValueError(f"Invalid SHAREPOINT_SITE_URL (missing host): {site_url}")

    parts = [p for p in (u.path or "/").split("/") if p]
    if len(parts) >= 2:
        site_path = f"/{parts[0]}/{parts[1]}"  # /sites/<name> or /teams/<name>
    else:
        site_path = "/"

    return domain, site_path

def register_sharepoint_tools(mcp: FastMCP) -> None:
    """
    Register read-only SharePoint MCP tools using AWS Credential Provider.
    Only includes tools that read/query data, no write/create/update/delete operations.
    
    Uses AWS Bedrock AgentCore Identity for OAuth2 token management.
    """

    @mcp.tool()
    async def get_sharepoint_site_info(ctx: Context) -> Dict[str, Any]:
        """
        Get basic information about the configured SharePoint site.
        
        Returns site details including name, description, URL, and creation date.
        Uses AWS Credential Provider for authentication.
        """
        logger.info("Tool called: get_sharepoint_site_info")
        
        try:
            app_ctx = _ctx(ctx)
            
            # Check if SharePoint context exists
            if not app_ctx.sharepoint_context:
                return {
                    "success": False,
                    "error": "SharePoint not configured",
                    "message": "Please configure SHAREPOINT_CALLBACK_URL and other SharePoint settings"
                }
            
            sp_ctx = app_ctx.sharepoint_context
            graph_client = app_ctx.graph_client
            
            # Extract site domain and path from configured site URL
            site_config = app_ctx.secrets.get("SHAREPOINT_SITE_URL", "").strip()
            
            if not site_config:
                return {
                    "success": False,
                    "error": "SHAREPOINT_SITE_URL not configured",
                    "message": "Please configure SHAREPOINT_SITE_URL in your environment"
                }
            
            domain, site_path = _parse_site_url(site_config)
            
            logger.info("Getting info for site_path=%s domain=%s", site_path, domain)
            
            # logger.info(f"Getting info for site: {site_path} in domain: {domain}")
            
            auth_url_holder = {}
            # Create decorated function to get access token from AWS
            @get_access_token_decorator(sp_ctx, on_auth_url=lambda url: auth_url_holder.setdefault("url", url))
            async def _get_site_info_with_token(*, access_token: str):
                """Inner function that receives the access token from AWS."""
                return await graph_client.get_site_info(domain, site_path, access_token)
            
            # Execute with token injection (AWS handles token automatically)
            try:
                site_info = await _get_site_info_with_token()
            except Exception as e:
                if auth_url_holder.get("url"):
                    return {
                        "success": False,
                        "error": "USER_CONSENT_REQUIRED",
                        "message": "Open the authorization_url to connect SharePoint, then retry.",
                        "authorization_url": auth_url_holder["url"],
                    }
                raise
            
            # Format response
            result = {
                "success": True,
                "site_name": site_info.get("displayName", "Unknown"),
                "description": site_info.get("description", "No description"),
                "created_date": site_info.get("createdDateTime", "Unknown"),
                "last_modified": site_info.get("lastModifiedDateTime", "Unknown"),
                "web_url": site_info.get("webUrl", site_config),
                "site_id": site_info.get("id", "Unknown")
            }
            
            logger.info(f"Successfully retrieved site info for: {result['site_name']}")
            return result
            
        except Exception as e:
            logger.exception(f"Error in get_sharepoint_site_info: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve SharePoint site information"
            }

    @mcp.tool()
    async def list_sharepoint_document_libraries(ctx: Context) -> Dict[str, Any]:
        """
        List all document libraries in the configured SharePoint site.
        
        Returns a list of document libraries with their names, descriptions, and URLs.
        Uses AWS Credential Provider for authentication.
        """
        logger.info("Tool called: list_sharepoint_document_libraries")
        
        try:
            app_ctx = _ctx(ctx)
            
            # Check if SharePoint context exists
            if not app_ctx.sharepoint_context:
                return {
                    "success": False,
                    "error": "SharePoint not configured",
                    "message": "Please configure SHAREPOINT_CALLBACK_URL and other SharePoint settings"
                }
            
            sp_ctx = app_ctx.sharepoint_context
            graph_client = app_ctx.graph_client
            
            # Extract site domain and path from configured site URL
            site_config = app_ctx.secrets.get("SHAREPOINT_SITE_URL", "")
            if not site_config:
                return {
                    "success": False,
                    "error": "SHAREPOINT_SITE_URL not configured",
                    "message": "Please configure SHAREPOINT_SITE_URL in your environment"
                }
            
            parts = [p for p in site_config.replace("https://", "").split("/") if p]
            domain = parts[0]
            
            if len(parts) >= 3:
                # "/sites/<name>" or "/teams/<name>"
                site_path = f"/{parts[1]}/{parts[2]}"
            else:
                # Root site
                site_path = "/"
            
            logger.info(f"Listing document libraries for site: {site_path} in domain: {domain}")
            
            # Create decorated function to get access token from AWS
            @get_access_token_decorator(sp_ctx)
            async def _list_libraries_with_token(*, access_token: str):
                """Inner function that receives the access token from AWS."""
                return await graph_client.list_document_libraries(domain, site_path, access_token)
            
            # Execute with token injection
            result = await _list_libraries_with_token()
            
            # Extract drive information from response
            drives = result.get("value", [])
            formatted_drives = [
                {
                    "name": drive.get("name", "Unknown"),
                    "description": drive.get("description", "No description"),
                    "web_url": drive.get("webUrl", "Unknown"),
                    "drive_type": drive.get("driveType", "Unknown"),
                    "drive_id": drive.get("id", "Unknown")
                }
                for drive in drives
            ]
            
            logger.info(f"Successfully retrieved {len(formatted_drives)} document libraries")
            return {
                "success": True,
                "count": len(formatted_drives),
                "libraries": formatted_drives
            }
            
        except Exception as e:
            logger.error(f"Error in list_sharepoint_document_libraries: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list SharePoint document libraries"
            }

    @mcp.tool()
    async def search_sharepoint(ctx: Context, query: str) -> Dict[str, Any]:
        """
        Search for content in the configured SharePoint site.

        Args:
            query: Search query string to find documents, lists, and other content
            
        Returns:
            Search results with titles, URLs, types, and summaries.
            Uses AWS Credential Provider for authentication.

        For USER_FEDERATION: uses delegated search (no region required).
        For M2M (application permissions): Graph requires `region` in the request body.

        Note: If `SHAREPOINT_SEARCH_REGION` is not available for M2M, this function falls back to
        SharePoint Drive search within the configured site (no region required) while preserving
        the same return format.
        """
        logger.info(f"Tool called: search_sharepoint with query: {query}")

        if not query or not query.strip():
            return {
                "success": False,
                "error": "Query parameter is required",
                "message": "Please provide a search query"
            }

        try:
            app_ctx = _ctx(ctx)

            # Check if SharePoint context exists
            if not app_ctx.sharepoint_context:
                return {
                    "success": False,
                    "error": "SharePoint not configured",
                    "message": "Please configure SHAREPOINT_CALLBACK_URL and other SharePoint settings"
                }

            sp_ctx = app_ctx.sharepoint_context
            graph_client = app_ctx.graph_client

            # Extract site domain and path from configured site URL
            site_config = (app_ctx.secrets.get("SHAREPOINT_SITE_URL") or "").strip()
            if not site_config:
                return {
                    "success": False,
                    "error": "SHAREPOINT_SITE_URL not configured",
                    "message": "Please configure SHAREPOINT_SITE_URL in your environment"
                }

            parts = [p for p in site_config.replace("https://", "").split("/") if p]
            if not parts:
                return {
                    "success": False,
                    "error": "Invalid SHAREPOINT_SITE_URL",
                    "message": f"Unable to parse SHAREPOINT_SITE_URL: {site_config}"
                }

            domain = parts[0]
            site_path = f"/{parts[1]}/{parts[2]}" if len(parts) >= 3 else "/"

            auth_url_holder: Dict[str, str] = {}

            @get_access_token_decorator(sp_ctx, on_auth_url=lambda url: auth_url_holder.setdefault("url", url))
            async def _search_with_token(*, access_token: str):
                # M2M: prefer Microsoft Search API with region if available; otherwise fallback to drive search.
                if sp_ctx.auth_flow == "M2M":
                    region = (app_ctx.secrets.get("SHAREPOINT_SEARCH_REGION") or "").strip()

                    if region:
                        # Use Graph beta search/query for application-permission SharePoint search
                        url = "https://graph.microsoft.com/beta/search/query"
                        payload = {
                            "requests": [
                                {
                                    "entityTypes": ["driveItem", "listItem", "list"],
                                    "query": {"queryString": f'{query} AND site:"{site_config}"'},
                                    "region": region,
                                }
                            ]
                        }
                        return await graph_client.post_url(url, payload, access_token)

                    # Fallback (no region): drive search within the configured site
                    site_info = await graph_client.get_site_info(domain, site_path, access_token)
                    logger.info(f"Sharepoint site info fetched: {site_info}")
                    site_id = site_info.get("id")
                    logger.info(f"Site ID retrieved: {site_id}")
                    if not site_id:
                        raise Exception("Could not resolve site_id for drive search fallback")

                    # Drive search endpoint (no region needed)
                    endpoint = f"sites/{site_id}/drive/root/search(q='{query}')"
                    return await graph_client.get(endpoint, access_token)

                # USER_FEDERATION: delegated search (no region requirement)
                payload = {
                    "requests": [
                        {
                            "entityTypes": ["driveItem", "listItem", "list"],
                            "query": {"queryString": query},
                        }
                    ]
                }
                return await graph_client.post("search/query", payload, access_token)

            try:
                search_results = await _search_with_token()
            except Exception:
                if auth_url_holder.get("url"):
                    return {
                        "success": False,
                        "error": "USER_CONSENT_REQUIRED",
                        "message": "Open the authorization_url to connect SharePoint, then retry.",
                        "authorization_url": auth_url_holder["url"],
                    }
                raise

            # ---- Parse results while preserving the return format ----
            formatted_results = []

            # Case 1: Microsoft Search API shape (beta/v1): hitsContainers
            hits_containers = search_results.get("hitsContainers")
            if hits_containers is None:
                hits_containers = (search_results.get("value") or [{}])[0].get("hitsContainers", None)

            if hits_containers is not None:
                for container in hits_containers or []:
                    for hit in container.get("hits", []) or []:
                        res = hit.get("resource", {}) or {}
                        formatted_results.append({
                            "title": res.get("name", "Unknown"),
                            "url": res.get("webUrl", "Unknown"),
                            "type": res.get("@odata.type", "Unknown"),
                            "summary": hit.get("summary", "No summary available"),
                        })
            else:
                # Case 2: Drive search fallback shape: { "value": [driveItem...] }
                for item in (search_results.get("value") or []):
                    # DriveItem has "name" + "webUrl"; type can be inferred
                    item_type = "folder" if "folder" in item else "file"
                    formatted_results.append({
                        "title": item.get("name", "Unknown"),
                        "url": item.get("webUrl", "Unknown"),
                        "type": item_type,
                        "summary": "Result returned from site drive search",
                    })

            return {
                "success": True,
                "query": query,
                "count": len(formatted_results),
                "results": formatted_results
            }

        except Exception as e:
            logger.exception("Error in search_sharepoint")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to search SharePoint for query: {query}"
            }

    @mcp.tool()
    async def get_sharepoint_list_items(
        ctx: Context,
        site_id: str,
        list_id: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get items from a SharePoint list.
        
        Args:
            site_id: ID of the SharePoint site
            list_id: ID or name of the list
            limit: Maximum number of items to retrieve (default: 100, max: 1000)
            
        Returns:
            List items with their fields and metadata.
            Uses AWS Credential Provider for authentication.
        """
        logger.info(f"Tool called: get_sharepoint_list_items for list: {list_id}")
        
        if not site_id or not list_id:
            return {
                "success": False,
                "error": "site_id and list_id are required",
                "message": "Please provide both site_id and list_id"
            }
        
        # Enforce limit bounds
        limit = max(1, min(limit, 1000))
        
        try:
            app_ctx = _ctx(ctx)
            
            # Check if SharePoint context exists
            if not app_ctx.sharepoint_context:
                return {
                    "success": False,
                    "error": "SharePoint not configured",
                    "message": "Please configure SHAREPOINT_CALLBACK_URL and other SharePoint settings"
                }
            
            sp_ctx = app_ctx.sharepoint_context
            graph_client = app_ctx.graph_client
            
            # Create decorated function to get access token from AWS
            @get_access_token_decorator(sp_ctx)
            async def _get_list_items_with_token(*, access_token: str):
                """Inner function that receives the access token from AWS."""
                endpoint = f"sites/{site_id}/lists/{list_id}/items?$expand=fields&$top={limit}"
                return await graph_client.get(endpoint, access_token)
            
            # Execute with token injection
            result = await _get_list_items_with_token()
            
            # Format items
            items = result.get("value", [])
            formatted_items = [
                {
                    "item_id": item.get("id"),
                    "created": item.get("createdDateTime"),
                    "modified": item.get("lastModifiedDateTime"),
                    "fields": item.get("fields", {})
                }
                for item in items
            ]
            
            logger.info(f"Successfully retrieved {len(formatted_items)} list items")
            return {
                "success": True,
                "site_id": site_id,
                "list_id": list_id,
                "count": len(formatted_items),
                "items": formatted_items
            }
            
        except Exception as e:
            logger.error(f"Error in get_sharepoint_list_items: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to retrieve list items from list: {list_id}"
            }

    @mcp.tool()
    async def get_sharepoint_document_content(
        ctx: Context,
        site_id: str,
        drive_id: str,
        item_id: str,
        file_name: str
    ) -> Dict[str, Any]:
        """
        Get content from a SharePoint document.
        
        Args:
            site_id: ID of the SharePoint site
            drive_id: ID of the document library (drive)
            item_id: ID of the document item
            file_name: Name of the file (used for content type detection)
            
        Returns:
            Document metadata and extracted text content (for supported file types).
            Uses AWS Credential Provider for authentication.
        """
        logger.info(f"Tool called: get_sharepoint_document_content for file: {file_name}")
        
        if not all([site_id, drive_id, item_id, file_name]):
            return {
                "success": False,
                "error": "All parameters are required",
                "message": "Please provide site_id, drive_id, item_id, and file_name"
            }
        
        try:
            app_ctx = _ctx(ctx)
            
            # Check if SharePoint context exists
            if not app_ctx.sharepoint_context:
                return {
                    "success": False,
                    "error": "SharePoint not configured",
                    "message": "Please configure SHAREPOINT_CALLBACK_URL and other SharePoint settings"
                }
            
            sp_ctx = app_ctx.sharepoint_context
            graph_client = app_ctx.graph_client
            
            # Create decorated function to get access token from AWS
            @get_access_token_decorator(sp_ctx)
            async def _get_document_with_token(*, access_token: str):
                """Inner function that receives the access token from AWS."""
                # Get document content
                content_bytes = await graph_client.get_document_content(
                    site_id, drive_id, item_id, access_token
                )
                
                # Get document metadata
                metadata_endpoint = f"sites/{site_id}/drives/{drive_id}/items/{item_id}"
                metadata = await graph_client.get(metadata_endpoint, access_token)
                
                return content_bytes, metadata
            
            # Execute with token injection
            content_bytes, metadata = await _get_document_with_token()
            
            # Process document content based on file type
            file_extension = file_name.lower().split('.')[-1] if '.' in file_name else ''
            
            result = {
                "success": True,
                "file_name": file_name,
                "file_size": len(content_bytes),
                "file_type": file_extension,
                "created": metadata.get("createdDateTime"),
                "modified": metadata.get("lastModifiedDateTime"),
                "created_by": metadata.get("createdBy", {}).get("user", {}).get("displayName"),
                "modified_by": metadata.get("lastModifiedBy", {}).get("user", {}).get("displayName"),
                "web_url": metadata.get("webUrl"),
            }
            
            # Try to extract text content for supported file types
            try:
                if DocumentProcessor.is_supported(file_name):
                    # Use DocumentProcessor utility
                    processed = DocumentProcessor.process_document(content_bytes, file_name)
                    result.update(processed)
                else:
                    result["content_extracted"] = False
                    result["message"] = f"Content extraction not supported for .{file_extension} files"
                    result["supported_formats"] = list(DocumentProcessor.get_supported_formats().keys())
            except Exception as extract_error:
                logger.warning(f"Failed to extract content from {file_name}: {str(extract_error)}")
                result["content_extracted"] = False
                result["extraction_error"] = str(extract_error)
            
            logger.info(f"Successfully retrieved document content for: {file_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error in get_sharepoint_document_content: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to retrieve document content for: {file_name}"
            }

    @mcp.tool()
    async def list_sharepoint_folder_contents(
        ctx: Context,
        site_id: str,
        drive_id: str,
        folder_path: str = ""
    ) -> Dict[str, Any]:
        """
        List contents of a folder in a SharePoint document library.
        
        Args:
            site_id: ID of the SharePoint site
            drive_id: ID of the document library (drive)
            folder_path: Path to the folder (empty string for root, e.g., "Documents/Subfolder")
            
        Returns:
            List of files and folders with their metadata.
            Uses AWS Credential Provider for authentication.
        """
        logger.info(f"Tool called: list_sharepoint_folder_contents for path: {folder_path or 'root'}")
        
        if not site_id or not drive_id:
            return {
                "success": False,
                "error": "site_id and drive_id are required",
                "message": "Please provide both site_id and drive_id"
            }
        
        try:
            app_ctx = _ctx(ctx)
            
            # Check if SharePoint context exists
            if not app_ctx.sharepoint_context:
                return {
                    "success": False,
                    "error": "SharePoint not configured",
                    "message": "Please configure SHAREPOINT_CALLBACK_URL and other SharePoint settings"
                }
            
            sp_ctx = app_ctx.sharepoint_context
            graph_client = app_ctx.graph_client
            
            # Create decorated function to get access token from AWS
            @get_access_token_decorator(sp_ctx)
            async def _list_folder_with_token(*, access_token: str):
                """Inner function that receives the access token from AWS."""
                # Build endpoint based on folder path
                if folder_path and folder_path.strip():
                    endpoint = f"sites/{site_id}/drives/{drive_id}/root:/{folder_path}:/children"
                else:
                    endpoint = f"sites/{site_id}/drives/{drive_id}/root/children"
                
                return await graph_client.get(endpoint, access_token)
            
            # Execute with token injection
            result = await _list_folder_with_token()
            
            # Format items
            items = result.get("value", [])
            formatted_items = []
            
            for item in items:
                formatted_item = {
                    "name": item.get("name"),
                    "id": item.get("id"),
                    "type": "folder" if "folder" in item else "file",
                    "size": item.get("size", 0),
                    "created": item.get("createdDateTime"),
                    "modified": item.get("lastModifiedDateTime"),
                    "web_url": item.get("webUrl")
                }
                
                # Add file-specific info
                if "file" in item:
                    formatted_item["mime_type"] = item.get("file", {}).get("mimeType")
                
                # Add folder-specific info
                if "folder" in item:
                    formatted_item["child_count"] = item.get("folder", {}).get("childCount", 0)
                
                formatted_items.append(formatted_item)
            
            logger.info(f"Successfully retrieved {len(formatted_items)} items from folder")
            return {
                "success": True,
                "site_id": site_id,
                "drive_id": drive_id,
                "folder_path": folder_path or "root",
                "count": len(formatted_items),
                "items": formatted_items
            }
            
        except Exception as e:
            logger.error(f"Error in list_sharepoint_folder_contents: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to list folder contents for path: {folder_path or 'root'}"
            }