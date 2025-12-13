"""
Tool layer for the self-correcting multi-agent system.

This module provides external tools that agents can use to gather information,
perform computations, and validate their responses.
"""

from .web_search import WebSearchTool
from .database_tool import DatabaseTool
from .code_executor import CodeExecutor
from .document_retriever import DocumentRetriever

__all__ = ['WebSearchTool', 'DatabaseTool', 'CodeExecutor', 'DocumentRetriever']