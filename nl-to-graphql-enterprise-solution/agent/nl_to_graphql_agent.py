"""Agent for converting natural language to GraphQL queries."""
import json
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage
from graphql_layer.schema import schema
from config import LLM_PROVIDER, LLM_MODEL, OPENAI_API_KEY, ANTHROPIC_API_KEY
from .prompts import (
    NL_TO_GRAPHQL_SYSTEM_PROMPT,
    VISUALIZATION_DECISION_PROMPT,
    ANSWER_GENERATION_PROMPT,
)


class NLToGraphQLAgent:
    """Agent that converts natural language queries to GraphQL and processes results."""
    
    def __init__(self):
        """Initialize the agent with the appropriate LLM."""
        if LLM_PROVIDER == "anthropic":
            self.llm = ChatAnthropic(
                model=LLM_MODEL,
                anthropic_api_key=ANTHROPIC_API_KEY,
                temperature=0,
            )
        else:
            self.llm = ChatOpenAI(
                model=LLM_MODEL,
                openai_api_key=OPENAI_API_KEY,
                temperature=0,
            )
    
    def generate_graphql_query(self, natural_language_query: str) -> str:
        """
        Convert a natural language query to a GraphQL query.
        
        Args:
            natural_language_query: The user's question in natural language
            
        Returns:
            A valid GraphQL query string
        """
        messages = [
            SystemMessage(content=NL_TO_GRAPHQL_SYSTEM_PROMPT),
            HumanMessage(content=natural_language_query),
        ]
        
        response = self.llm.invoke(messages)
        graphql_query = response.content.strip()
        
        # Clean up any markdown formatting if present
        if graphql_query.startswith("```"):
            lines = graphql_query.split("\n")
            graphql_query = "\n".join(lines[1:-1]) if len(lines) > 2 else graphql_query
        
        return graphql_query
    
    def execute_graphql_query(self, query: str) -> Dict[str, Any]:
        """
        Execute a GraphQL query against the schema.
        
        Args:
            query: A valid GraphQL query string
            
        Returns:
            The query result as a dictionary
        """
        try:
            result = schema.execute_sync(query)
            
            if result.errors:
                return {
                    "success": False,
                    "errors": [str(e) for e in result.errors],
                    "data": None,
                }
            
            return {
                "success": True,
                "errors": None,
                "data": result.data,
            }
        except Exception as e:
            return {
                "success": False,
                "errors": [str(e)],
                "data": None,
            }
    
    def decide_visualization(
        self, 
        question: str, 
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Decide what type of visualization is appropriate for the data.
        
        Args:
            question: The user's original question
            data: The retrieved data
            
        Returns:
            A dictionary with visualization configuration
        """
        # Create a summary of the data
        data_summary = self._summarize_data(data)
        
        prompt = VISUALIZATION_DECISION_PROMPT.format(
            question=question,
            data_summary=data_summary,
        )
        
        messages = [
            HumanMessage(content=prompt),
        ]
        
        response = self.llm.invoke(messages)
        
        try:
            # Parse the JSON response
            viz_config = json.loads(response.content.strip())
            return viz_config
        except json.JSONDecodeError:
            # If parsing fails, return a default table view
            return {
                "chart_type": "table",
                "x_field": None,
                "y_field": None,
                "title": "Data Results",
                "reasoning": "Unable to determine appropriate visualization",
            }
    
    def generate_answer(self, question: str, data: Dict[str, Any]) -> str:
        """
        Generate a natural language answer based on the question and data.
        
        Args:
            question: The user's original question
            data: The retrieved data
            
        Returns:
            A natural language answer
        """
        prompt = ANSWER_GENERATION_PROMPT.format(
            question=question,
            data=json.dumps(data, indent=2, default=str),
        )
        
        messages = [
            HumanMessage(content=prompt),
        ]
        
        response = self.llm.invoke(messages)
        return response.content.strip()
    
    def _summarize_data(self, data: Dict[str, Any]) -> str:
        """Create a brief summary of the data structure."""
        if not data:
            return "No data"
        
        summary_parts = []
        for key, value in data.items():
            if isinstance(value, list):
                summary_parts.append(f"{key}: list of {len(value)} items")
                if value and isinstance(value[0], dict):
                    summary_parts.append(f"  Fields: {', '.join(value[0].keys())}")
            elif isinstance(value, dict):
                summary_parts.append(f"{key}: object with fields {', '.join(value.keys())}")
            else:
                summary_parts.append(f"{key}: {type(value).__name__}")
        
        return "\n".join(summary_parts)
    
    def process_query(self, natural_language_query: str) -> Dict[str, Any]:
        """
        Process a complete natural language query end-to-end.
        
        Args:
            natural_language_query: The user's question
            
        Returns:
            A dictionary containing the GraphQL query, data, answer, and visualization config
        """
        print(f"\n🔍 Processing query: {natural_language_query}")
        
        # Step 1: Generate GraphQL query
        print("📝 Generating GraphQL query...")
        graphql_query = self.generate_graphql_query(natural_language_query)
        print(f"Generated query:\n{graphql_query}\n")
        
        # Step 2: Execute the query
        print("⚡ Executing GraphQL query...")
        result = self.execute_graphql_query(graphql_query)
        
        if not result["success"]:
            return {
                "success": False,
                "graphql_query": graphql_query,
                "errors": result["errors"],
                "data": None,
                "answer": f"Error executing query: {', '.join(result['errors'])}",
                "visualization": None,
            }
        
        data = result["data"]
        print(f"✅ Query executed successfully!")
        
        # Step 3: Decide on visualization
        print("📊 Determining visualization...")
        viz_config = self.decide_visualization(natural_language_query, data)
        print(f"Visualization: {viz_config['chart_type']} - {viz_config['reasoning']}")
        
        # Step 4: Generate natural language answer
        print("💬 Generating answer...")
        answer = self.generate_answer(natural_language_query, data)
        
        return {
            "success": True,
            "graphql_query": graphql_query,
            "errors": None,
            "data": data,
            "answer": answer,
            "visualization": viz_config,
        }
