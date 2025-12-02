"""
MCP Server for Natural Language to Data Endpoints
Supports SQL, NoSQL, Cypher, and GraphQL conversions with multiple database connectivity
"""

import os
import json
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv

from connectors.sql_connector import SQLConnector
from connectors.nosql_connector import NoSQLConnector
from connectors.graph_connector import GraphConnector
from connectors.graphql_connector import GraphQLConnector
from llm.provider import LLMProvider
from cache.schema_cache import SchemaCache

# Load environment variables
load_dotenv()

# Initialize MCP Server
app = Server("nl-to-data-endpoints")

# Initialize components
llm_provider = LLMProvider()
schema_cache = SchemaCache()

# Initialize connectors
sql_connector = SQLConnector(schema_cache)
nosql_connector = NoSQLConnector(schema_cache)
graph_connector = GraphConnector(schema_cache)
graphql_connector = GraphQLConnector(schema_cache)


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="nl_to_sql",
            description="Convert natural language query to SQL and execute it. Supports MySQL, PostgreSQL, Oracle, MS-SQL, Snowflake, Databricks, AWS RDS, GCP, Azure databases.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query"},
                    "database_type": {"type": "string", "description": "Database type (mysql, postgresql, oracle, mssql, snowflake, databricks)"},
                    "execute": {"type": "boolean", "description": "Whether to execute the query", "default": False}
                },
                "required": ["query", "database_type"]
            }
        ),
        Tool(
            name="nl_to_nosql",
            description="Convert natural language query to NoSQL and execute it. Supports MongoDB, Cassandra, Redis, DynamoDB, Snowflake, Databricks, GCP, Azure databases.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query"},
                    "database_type": {"type": "string", "description": "Database type (mongodb, cassandra, redis, dynamodb)"},
                    "execute": {"type": "boolean", "description": "Whether to execute the query", "default": False}
                },
                "required": ["query", "database_type"]
            }
        ),
        Tool(
            name="nl_to_cypher",
            description="Convert natural language query to Cypher and execute it. Supports Neo4j, ArangoDB, GraphDB, Amazon Neptune, Azure CosmosDB.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query"},
                    "database_type": {"type": "string", "description": "Database type (neo4j, arangodb, graphdb, neptune, cosmosdb)"},
                    "execute": {"type": "boolean", "description": "Whether to execute the query", "default": False}
                },
                "required": ["query", "database_type"]
            }
        ),
        Tool(
            name="nl_to_graphql",
            description="Convert natural language query to GraphQL and execute it. Supports various GraphQL APIs including Saleor.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query"},
                    "api_endpoint": {"type": "string", "description": "GraphQL API endpoint URL"},
                    "execute": {"type": "boolean", "description": "Whether to execute the query", "default": False}
                },
                "required": ["query", "api_endpoint"]
            }
        ),
        Tool(
            name="refresh_schema_cache",
            description="Refresh the cached schema for a specific database connection",
            inputSchema={
                "type": "object",
                "properties": {
                    "connector_type": {"type": "string", "description": "Connector type (sql, nosql, graph, graphql)"},
                    "database_type": {"type": "string", "description": "Specific database type"}
                },
                "required": ["connector_type", "database_type"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls"""
    
    if name == "nl_to_sql":
        return await handle_nl_to_sql(arguments)
    elif name == "nl_to_nosql":
        return await handle_nl_to_nosql(arguments)
    elif name == "nl_to_cypher":
        return await handle_nl_to_cypher(arguments)
    elif name == "nl_to_graphql":
        return await handle_nl_to_graphql(arguments)
    elif name == "refresh_schema_cache":
        return await handle_refresh_cache(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_nl_to_sql(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle natural language to SQL conversion"""
    query = arguments["query"]
    database_type = arguments["database_type"]
    execute = arguments.get("execute", False)
    
    try:
        # Get schema from cache or fetch
        schema = await sql_connector.get_schema(database_type)
        
        # Generate SQL using LLM
        sql_query = await llm_provider.generate_sql(query, schema, database_type)
        
        result = {
            "generated_sql": sql_query,
            "database_type": database_type
        }
        
        # Execute if requested
        if execute:
            execution_result = await sql_connector.execute_query(sql_query, database_type)
            result["execution_result"] = execution_result
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_nl_to_nosql(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle natural language to NoSQL conversion"""
    query = arguments["query"]
    database_type = arguments["database_type"]
    execute = arguments.get("execute", False)
    
    try:
        # Get schema from cache or fetch
        schema = await nosql_connector.get_schema(database_type)
        
        # Generate NoSQL query using LLM
        nosql_query = await llm_provider.generate_nosql(query, schema, database_type)
        
        result = {
            "generated_query": nosql_query,
            "database_type": database_type
        }
        
        # Execute if requested
        if execute:
            execution_result = await nosql_connector.execute_query(nosql_query, database_type)
            result["execution_result"] = execution_result
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_nl_to_cypher(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle natural language to Cypher conversion"""
    query = arguments["query"]
    database_type = arguments["database_type"]
    execute = arguments.get("execute", False)
    
    try:
        # Get schema from cache or fetch
        schema = await graph_connector.get_schema(database_type)
        
        # Generate Cypher query using LLM
        cypher_query = await llm_provider.generate_cypher(query, schema, database_type)
        
        result = {
            "generated_cypher": cypher_query,
            "database_type": database_type
        }
        
        # Execute if requested
        if execute:
            execution_result = await graph_connector.execute_query(cypher_query, database_type)
            result["execution_result"] = execution_result
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_nl_to_graphql(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle natural language to GraphQL conversion"""
    query = arguments["query"]
    api_endpoint = arguments["api_endpoint"]
    execute = arguments.get("execute", False)
    
    try:
        # Get schema from cache or fetch
        schema = await graphql_connector.get_schema(api_endpoint)
        
        # Generate GraphQL query using LLM
        graphql_query = await llm_provider.generate_graphql(query, schema)
        
        result = {
            "generated_graphql": graphql_query,
            "api_endpoint": api_endpoint
        }
        
        # Execute if requested
        if execute:
            execution_result = await graphql_connector.execute_query(graphql_query, api_endpoint)
            result["execution_result"] = execution_result
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_refresh_cache(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle schema cache refresh"""
    connector_type = arguments["connector_type"]
    database_type = arguments["database_type"]
    
    try:
        if connector_type == "sql":
            await sql_connector.refresh_schema(database_type)
        elif connector_type == "nosql":
            await nosql_connector.refresh_schema(database_type)
        elif connector_type == "graph":
            await graph_connector.refresh_schema(database_type)
        elif connector_type == "graphql":
            await graphql_connector.refresh_schema(database_type)
        else:
            return [TextContent(type="text", text=f"Unknown connector type: {connector_type}")]
        
        return [TextContent(type="text", text=f"Schema cache refreshed for {connector_type}/{database_type}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
