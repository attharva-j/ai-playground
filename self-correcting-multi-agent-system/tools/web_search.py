"""
Web Search Tool - Provides web search capabilities for agents.
"""

import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from tavily import TavilyClient

@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = None

class WebSearchTool:
    """
    Web search tool using Tavily API for reliable, factual information retrieval.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY is required for web search functionality")
        
        self.client = TavilyClient(api_key=self.api_key)
    
    def search(
        self, 
        query: str, 
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Perform a web search and return structured results.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            include_domains: List of domains to include (optional)
            exclude_domains: List of domains to exclude (optional)
            
        Returns:
            List of SearchResult objects
        """
        try:
            # Perform the search
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_domains=include_domains,
                exclude_domains=exclude_domains
            )
            
            # Convert to SearchResult objects
            results = []
            for item in response.get("results", []):
                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                    published_date=item.get("published_date")
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Web search error: {e}")
            return []
    
    def search_with_context(self, query: str, context: str = "") -> str:
        """
        Perform a search and return formatted context for agents.
        
        Args:
            query: Search query
            context: Additional context to include in formatting
            
        Returns:
            Formatted search results as a string
        """
        results = self.search(query, max_results=3)
        
        if not results:
            return f"No search results found for: {query}"
        
        formatted = f"Search Results for '{query}':\n\n"
        
        for i, result in enumerate(results, 1):
            formatted += f"{i}. **{result.title}**\n"
            formatted += f"   URL: {result.url}\n"
            formatted += f"   Content: {result.content[:300]}...\n"
            if result.published_date:
                formatted += f"   Published: {result.published_date}\n"
            formatted += f"   Relevance Score: {result.score:.2f}\n\n"
        
        return formatted
    
    def verify_claim(self, claim: str) -> Dict[str, Any]:
        """
        Verify a factual claim using web search.
        
        Args:
            claim: The claim to verify
            
        Returns:
            Dictionary with verification results
        """
        # Search for the claim
        results = self.search(f"verify fact: {claim}", max_results=3)
        
        verification = {
            "claim": claim,
            "sources_found": len(results),
            "verification_confidence": 0.0,
            "supporting_sources": [],
            "contradicting_sources": [],
            "summary": ""
        }
        
        if not results:
            verification["summary"] = "No sources found to verify this claim"
            return verification
        
        # Analyze results for support/contradiction
        supporting = []
        contradicting = []
        
        for result in results:
            content_lower = result.content.lower()
            claim_lower = claim.lower()
            
            # Simple heuristic for support/contradiction
            if any(word in content_lower for word in claim_lower.split()):
                supporting.append({
                    "title": result.title,
                    "url": result.url,
                    "excerpt": result.content[:200] + "...",
                    "score": result.score
                })
        
        verification["supporting_sources"] = supporting
        verification["verification_confidence"] = min(len(supporting) * 0.3, 1.0)
        
        if supporting:
            verification["summary"] = f"Found {len(supporting)} sources that may support this claim"
        else:
            verification["summary"] = "No clear supporting sources found for this claim"
        
        return verification

# Example usage and testing
def test_web_search():
    """Test function for web search tool."""
    try:
        search_tool = WebSearchTool()
        
        # Test basic search
        results = search_tool.search("artificial intelligence latest developments", max_results=2)
        print(f"Found {len(results)} results")
        
        for result in results:
            print(f"- {result.title}: {result.content[:100]}...")
        
        # Test claim verification
        verification = search_tool.verify_claim("The capital of France is Paris")
        print(f"Verification confidence: {verification['verification_confidence']}")
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_web_search()