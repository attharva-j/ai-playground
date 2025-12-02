"""
LLM Provider for generating queries from natural language
Supports OpenAI and Anthropic
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()


class LLMProvider:
    """Pluggable LLM provider supporting OpenAI and Anthropic"""
    
    def __init__(self):
        self.provider = os.getenv("MCP_LLM_PROVIDER", "openai").lower()
        self.model = os.getenv("MCP_LLM_MODEL")
        
        if self.provider == "openai":
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            if not self.model:
                self.model = "gpt-4"
        elif self.provider == "anthropic":
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            if not self.model:
                self.model = "claude-3-sonnet-20240229"
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    async def generate_sql(self, nl_query: str, schema: Dict[str, Any], database_type: str) -> str:
        """Generate SQL query from natural language"""
        prompt = self._build_sql_prompt(nl_query, schema, database_type)
        return await self._generate(prompt)
    
    async def generate_nosql(self, nl_query: str, schema: Dict[str, Any], database_type: str) -> str:
        """Generate NoSQL query from natural language"""
        prompt = self._build_nosql_prompt(nl_query, schema, database_type)
        return await self._generate(prompt)
    
    async def generate_cypher(self, nl_query: str, schema: Dict[str, Any], database_type: str) -> str:
        """Generate Cypher query from natural language"""
        prompt = self._build_cypher_prompt(nl_query, schema, database_type)
        return await self._generate(prompt)
    
    async def generate_graphql(self, nl_query: str, schema: Dict[str, Any]) -> str:
        """Generate GraphQL query from natural language"""
        prompt = self._build_graphql_prompt(nl_query, schema)
        return await self._generate(prompt)
    
    async def _generate(self, prompt: str) -> str:
        """Generate response using configured LLM provider"""
        if self.provider == "openai":
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert database query generator. Generate only the query without explanations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        
        elif self.provider == "anthropic":
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                system="You are an expert database query generator. Generate only the query without explanations.",
                temperature=0.1
            )
            return response.content[0].text.strip()
    
    def _build_sql_prompt(self, nl_query: str, schema: Dict[str, Any], database_type: str) -> str:
        """Build prompt for SQL generation"""
        return f"""Generate a {database_type.upper()} SQL query for the following request.

Database Schema:
{self._format_schema(schema)}

Natural Language Query: {nl_query}

Generate ONLY the SQL query, no explanations. Use {database_type}-specific syntax and best practices."""
    
    def _build_nosql_prompt(self, nl_query: str, schema: Dict[str, Any], database_type: str) -> str:
        """Build prompt for NoSQL generation"""
        return f"""Generate a {database_type.upper()} query for the following request.

Database Schema:
{self._format_schema(schema)}

Natural Language Query: {nl_query}

Generate ONLY the {database_type} query, no explanations. Use {database_type}-specific syntax and best practices."""
    
    def _build_cypher_prompt(self, nl_query: str, schema: Dict[str, Any], database_type: str) -> str:
        """Build prompt for Cypher generation"""
        return f"""Generate a Cypher query for {database_type} for the following request.

Graph Schema:
{self._format_schema(schema)}

Natural Language Query: {nl_query}

Generate ONLY the Cypher query, no explanations. Use {database_type}-specific syntax and best practices."""
    
    def _build_graphql_prompt(self, nl_query: str, schema: Dict[str, Any]) -> str:
        """Build prompt for GraphQL generation"""
        return f"""Generate a GraphQL query for the following request.

GraphQL Schema:
{self._format_schema(schema)}

Natural Language Query: {nl_query}

Generate ONLY the GraphQL query, no explanations."""
    
    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format schema for prompt"""
        import json
        return json.dumps(schema, indent=2)
