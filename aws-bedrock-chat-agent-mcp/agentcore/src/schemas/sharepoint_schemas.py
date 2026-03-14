"""Pydantic schemas for SharePoint MCP tool responses."""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class SharePointSiteInfo(BaseModel):
    """SharePoint site information response."""
    
    success: bool = Field(description="Whether the operation was successful")
    site_name: Optional[str] = Field(None, description="Display name of the site")
    description: Optional[str] = Field(None, description="Site description")
    created_date: Optional[str] = Field(None, description="Site creation date")
    last_modified: Optional[str] = Field(None, description="Last modification date")
    web_url: Optional[str] = Field(None, description="Web URL of the site")
    site_id: Optional[str] = Field(None, description="Unique site identifier")
    error: Optional[str] = Field(None, description="Error message if failed")
    message: Optional[str] = Field(None, description="Human-readable message")


class DocumentLibrary(BaseModel):
    """Document library metadata."""
    
    name: str = Field(description="Library name")
    description: Optional[str] = Field(None, description="Library description")
    web_url: str = Field(description="Web URL of the library")
    drive_type: str = Field(description="Type of drive")
    drive_id: str = Field(description="Unique drive identifier")


class DocumentLibrariesResponse(BaseModel):
    """Response for listing document libraries."""
    
    success: bool = Field(description="Whether the operation was successful")
    count: Optional[int] = Field(None, description="Number of libraries found")
    libraries: Optional[List[DocumentLibrary]] = Field(None, description="List of document libraries")
    error: Optional[str] = Field(None, description="Error message if failed")
    message: Optional[str] = Field(None, description="Human-readable message")


class SearchResult(BaseModel):
    """SharePoint search result item."""
    
    title: str = Field(description="Title of the result")
    url: str = Field(description="URL of the result")
    type: str = Field(description="Type of the result (driveItem, listItem, etc.)")
    summary: Optional[str] = Field(None, description="Summary or snippet")


class SearchResponse(BaseModel):
    """Response for SharePoint search."""
    
    success: bool = Field(description="Whether the operation was successful")
    query: Optional[str] = Field(None, description="Search query used")
    count: Optional[int] = Field(None, description="Number of results found")
    results: Optional[List[SearchResult]] = Field(None, description="Search results")
    error: Optional[str] = Field(None, description="Error message if failed")
    message: Optional[str] = Field(None, description="Human-readable message")


class ListItem(BaseModel):
    """SharePoint list item."""
    
    item_id: str = Field(description="Item identifier")
    created: Optional[str] = Field(None, description="Creation date")
    modified: Optional[str] = Field(None, description="Last modification date")
    fields: Dict[str, Any] = Field(default_factory=dict, description="Item fields")


class ListItemsResponse(BaseModel):
    """Response for getting list items."""
    
    success: bool = Field(description="Whether the operation was successful")
    site_id: Optional[str] = Field(None, description="Site identifier")
    list_id: Optional[str] = Field(None, description="List identifier")
    count: Optional[int] = Field(None, description="Number of items")
    items: Optional[List[ListItem]] = Field(None, description="List items")
    error: Optional[str] = Field(None, description="Error message if failed")
    message: Optional[str] = Field(None, description="Human-readable message")


class DocumentContent(BaseModel):
    """Document content and metadata."""
    
    success: bool = Field(description="Whether the operation was successful")
    file_name: Optional[str] = Field(None, description="Name of the file")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_type: Optional[str] = Field(None, description="File extension")
    created: Optional[str] = Field(None, description="Creation date")
    modified: Optional[str] = Field(None, description="Last modification date")
    created_by: Optional[str] = Field(None, description="Creator name")
    modified_by: Optional[str] = Field(None, description="Last modifier name")
    web_url: Optional[str] = Field(None, description="Web URL of the document")
    content: Optional[str] = Field(None, description="Extracted text content")
    content_extracted: Optional[bool] = Field(None, description="Whether content was extracted")
    extraction_error: Optional[str] = Field(None, description="Error during extraction")
    page_count: Optional[int] = Field(None, description="Number of pages (for PDFs)")
    paragraph_count: Optional[int] = Field(None, description="Number of paragraphs (for Word)")
    rows: Optional[int] = Field(None, description="Number of rows (for Excel)")
    columns: Optional[int] = Field(None, description="Number of columns (for Excel)")
    error: Optional[str] = Field(None, description="Error message if failed")
    message: Optional[str] = Field(None, description="Human-readable message")


class FolderItem(BaseModel):
    """File or folder item in a document library."""
    
    name: str = Field(description="Item name")
    id: str = Field(description="Item identifier")
    type: str = Field(description="Item type (file or folder)")
    size: int = Field(description="Size in bytes")
    created: Optional[str] = Field(None, description="Creation date")
    modified: Optional[str] = Field(None, description="Last modification date")
    web_url: str = Field(description="Web URL of the item")
    mime_type: Optional[str] = Field(None, description="MIME type (for files)")
    child_count: Optional[int] = Field(None, description="Number of children (for folders)")


class FolderContentsResponse(BaseModel):
    """Response for listing folder contents."""
    
    success: bool = Field(description="Whether the operation was successful")
    site_id: Optional[str] = Field(None, description="Site identifier")
    drive_id: Optional[str] = Field(None, description="Drive identifier")
    folder_path: Optional[str] = Field(None, description="Folder path")
    count: Optional[int] = Field(None, description="Number of items")
    items: Optional[List[FolderItem]] = Field(None, description="Folder items")
    error: Optional[str] = Field(None, description="Error message if failed")
    message: Optional[str] = Field(None, description="Human-readable message")