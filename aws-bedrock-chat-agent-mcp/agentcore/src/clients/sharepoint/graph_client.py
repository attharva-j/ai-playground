"""Microsoft Graph API client for SharePoint operations."""

from __future__ import annotations

import logging
from typing import Dict, Any

import requests

from clients.sharepoint.auth import SharePointContext

logger = logging.getLogger("graph_client")


class GraphClient:
    """Client for interacting with Microsoft Graph API using AWS Credential Provider."""
    
    def __init__(self, context: SharePointContext):
        """
        Initialize Graph API client with SharePoint context.
        
        Args:
            context: SharePoint authentication context configured for AWS Credential Provider
        """
        self.context = context
        self.base_url = context.graph_url
        logger.debug(f"GraphClient initialized with base URL: {self.base_url}")
    
    async def get(self, endpoint: str, access_token: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Send GET request to Microsoft Graph API.
        
        Args:
            endpoint: API endpoint path (without base URL)
            access_token: OAuth2 access token from credential provider
            timeout: Request timeout in seconds
            
        Returns:
            Response from the API as dictionary
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.debug(f"Making GET request to: {url}")
        
        # Get headers with access token
        headers = self.context.get_headers(access_token)
        
        # Send request
        response = requests.get(url, headers=headers, timeout=timeout)
        
        # Log response
        logger.debug(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"Graph API error: {response.status_code} - {error_text}")
            
            # Log detailed info for auth errors
            if response.status_code in (401, 403):
                logger.error("Authentication or authorization error detected")
                if "scp or roles claim" in error_text:
                    logger.error("Token does not have required claims (scp or roles)")
                    logger.error("Please check application permissions in Azure AD")
            
            raise Exception(f"Graph API error: {response.status_code} - {error_text}")
        
        # Return successful response as JSON
        return response.json()
    
    async def post(self, endpoint: str, data: Dict[str, Any], access_token: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Send POST request to Microsoft Graph API.
        
        Args:
            endpoint: API endpoint path (without base URL)
            data: JSON data to send
            access_token: OAuth2 access token from credential provider
            timeout: Request timeout in seconds
            
        Returns:
            Response from the API as dictionary
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.debug(f"Making POST request to: {url}")
        logger.debug(f"With data: {data}")
        
        # Get headers with access token
        headers = self.context.get_headers(access_token)
        
        # Send request
        response = requests.post(url, headers=headers, json=data, timeout=timeout)
        
        # Log response
        logger.debug(f"Response status code: {response.status_code}")
        
        if response.status_code not in (200, 201):
            error_text = response.text
            logger.error(f"Graph API error: {response.status_code} - {error_text}")
            
            # Log detailed info for auth errors
            if response.status_code in (401, 403):
                logger.error("Authentication or authorization error detected")
                if "scp or roles claim" in error_text:
                    logger.error("Token does not have required claims (scp or roles)")
                    logger.error("Please check application permissions in Azure AD")
            
            raise Exception(f"Graph API error: {response.status_code} - {error_text}")
        
        # Return successful response as JSON
        return response.json()
    
    async def get_site_info(self, domain: str, site_path: str, access_token: str) -> Dict[str, Any]:
        """
        Get SharePoint site information using Graph 'getByPath' style:
        - root:    sites/{domain}:
        - nonroot: sites/{domain}:{site_path}
        site_path example: "/sites/MySite" or "/teams/MyTeam"
        """
        site_path = (site_path or "").strip()
        if not site_path or site_path == "/":
            endpoint = f"sites/{domain}:"
        else:
            if not site_path.startswith("/"):
                site_path = "/" + site_path
            endpoint = f"sites/{domain}:{site_path}"

        logger.info(f"Getting site info for domain={domain} path={site_path or '/'}")
        return await self.get(endpoint, access_token)
    
    async def list_document_libraries(self, domain: str, site_path: str, access_token: str) -> Dict[str, Any]:
        """
        List all document libraries (drives) in the SharePoint site.
        
        Args:
            domain: SharePoint domain
            site_name: Name of the site (use "root" or empty string for root site)
            access_token: OAuth2 access token from credential provider
            
        Returns:
            List of document libraries with their metadata

        List all document libraries (drives) in the SharePoint site.
        site_path examples: "/sites/aifactory", "/teams/foo", "/"
        """
        site_info = await self.get_site_info(domain, site_path, access_token)
        site_id = site_info.get("id")
        if not site_id:
            raise Exception(f"Failed to get site ID for domain={domain}, site_path={site_path}")

        endpoint = f"sites/{site_id}/drives"
        logger.info("Listing document libraries for site_id=%s", site_id)
        return await self.get(endpoint, access_token)
    
    async def get_document_content(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
        access_token: str
    ) -> bytes:
        """
        Get content of a document from SharePoint.
        
        Args:
            site_id: ID of the SharePoint site
            drive_id: ID of the document library (drive)
            item_id: ID of the document item
            access_token: OAuth2 access token from credential provider
        
        Returns:
            Document content as bytes
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.base_url}/sites/{site_id}/drives/{drive_id}/items/{item_id}/content"
        headers = self.context.get_headers(access_token).copy()
        # Remove Content-Type header to respect response Content-Type
        headers.pop("Content-Type", None)
        
        logger.info(f"Getting document content for item {item_id}")
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        
        if response.status_code != 200:
            error_text = response.text
            logger.error(f"Graph API error: {response.status_code} - {error_text}")
            raise Exception(f"Graph API error: {response.status_code} - {error_text}")
        
        return response.content
    
    async def post_url(self, url: str, data: Dict[str, Any], access_token: str, timeout: int = 30) -> Dict[str, Any]:
        """
        POST to an absolute URL (used for Graph beta endpoints).
        """
        headers = self.context.get_headers(access_token)
        response = requests.post(url, headers=headers, json=data, timeout=timeout)

        logger.debug(f"POST {url} -> {response.status_code}")

        if response.status_code not in (200, 201):
            error_text = response.text
            logger.error(f"Graph API error: {response.status_code} - {error_text}")
            raise Exception(f"Graph API error: {response.status_code} - {error_text}")

        return response.json()