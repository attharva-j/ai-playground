# Implementation Details - MCP Natural Language to Data Endpoints

## Architecture Overview

The MCP Natural Language to Data Endpoints server is built using a modular architecture that separates concerns between protocol handling, query generation, database connectivity, and caching.

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP Client                            │
│                   (Claude Desktop, etc.)                     │
└────────────────────────┬────────────────────────────────────┘
                         │ stdio (MCP Protocol)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   server.py (MCP Server)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tool Handlers:                                       │  │
│  │  • nl_to_sql_handler                                 │  │
│  │  • nl_to_nosql_handler                               │  │
│  │  • nl_to_cypher_handler                              │  │
│  │  • nl_to_graphql_handler                             │  │
│  │  • refresh_schema_cache_handler                      │  │
│  └──────────────────────────────────────────────────────┘  │
└────────┬──────────────────┬──────────────────┬─────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐ ┌──────────────┐ ┌─────────────────┐
│   Connectors    │ │ LLM Provider │ │  Schema Cache   │
│   (connectors/) │ │ (llm/)       │ │  (cache/)       │
│                 │ │              │ │                 │
│ • sql_conn.py   │ │ • provider.py│ │ • schema_cache  │
│ • nosql_conn.py │ │              │ │   .py           │
│ • graph_conn.py │ │ OpenAI/      │ │                 │
│ • graphql_conn  │ │ Anthropic    │ │ File-based      │
│   .py           │ │              │ │ TTL: 24h        │
└────────┬────────┘ └──────────────┘ └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database Systems                          │
│  SQL • NoSQL • Graph • GraphQL                              │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. MCP Server (server.py)

The main entry point that implements the Model Context Protocol:

```python
# Key responsibilities:
- Initialize MCP server with stdio transport
- Register tool handlers
- Process incoming tool requests
- Return structured responses
- Handle errors and logging
```

**Tool Registration:**
- `nl_to_sql`: Natural language to SQL query generation
- `nl_to_nosql`: Natural language to NoSQL query generation
- `nl_to_cypher`: Natural language to Cypher query generation
- `nl_to_graphql`: Natural language to GraphQL query generation
- `refresh_schema_cache`: Manual schema cache refresh

### 2. Connectors (connectors/)

Database-specific connection and query handling:

#### SQL Connector (`sql_connector.py`)
```python
class SQLConnector:
    - connect(): Establish database connection
    - get_schema(): Introspect database schema
    - execute_query(): Run SQL query
    - format_results(): Convert results to JSON
```

Supported SQL databases:
- MySQL/MariaDB
- PostgreSQL
- Oracle
- MS-SQL Server
- Snowflake
- Databricks
- AWS RDS
- GCP Cloud SQL
- Azure SQL

#### NoSQL Connector (`nosql_connector.py`)
```python
class NoSQLConnector:
    - connect(): Establish connection
    - get_schema(): Sample documents for schema
    - execute_query(): Run NoSQL query
    - format_results(): Convert to JSON
```

Supported NoSQL databases:
- MongoDB (aggregation pipelines)
- Cassandra (CQL)
- Redis (commands)
- DynamoDB (query/scan)

#### Graph Connector (`graph_connector.py`)
```python
class GraphConnector:
    - connect(): Establish connection
    - get_schema(): Get node/edge types
    - execute_query(): Run graph query
    - format_results(): Convert to JSON
```

Supported graph databases:
- Neo4j (Cypher)
- ArangoDB (AQL)
- GraphDB (SPARQL)
- Amazon Neptune (Gremlin)
- Azure CosmosDB (Gremlin)

#### GraphQL Connector (`graphql_connector.py`)
```python
class GraphQLConnector:
    - connect(): Setup HTTP client
    - get_schema(): Introspect GraphQL schema
    - execute_query(): Send GraphQL request
    - format_results(): Parse response
```

### 3. LLM Provider (llm/provider.py)

Handles query generation using LLMs:

```python
class LLMProvider:
    def __init__(self, provider: str, model: str):
        # Initialize OpenAI or Anthropic client
        
    def generate_query(
        self,
        natural_language: str,
        schema: dict,
        query_type: str
    ) -> str:
        # Build context-aware prompt
        # Call LLM API
        # Extract and validate query
        # Return generated query
```

**Prompt Engineering:**
- Include full schema context
- Specify database-specific syntax
- Provide examples for complex queries
- Request optimized queries
- Handle edge cases

**Supported Models:**
- OpenAI: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- Anthropic: claude-3-opus, claude-3-sonnet, claude-3-haiku

### 4. Schema Cache (cache/schema_cache.py)

Performance optimization through caching:

```python
class SchemaCache:
    def __init__(self, cache_dir: str, ttl: int = 86400):
        # Initialize cache directory
        # Set TTL (default 24 hours)
        
    def get(self, key: str) -> Optional[dict]:
        # Check if cached schema exists
        # Verify TTL hasn't expired
        # Return cached schema or None
        
    def set(self, key: str, schema: dict):
        # Serialize schema to JSON
        # Write to cache file
        # Set timestamp
        
    def invalidate(self, key: str):
        # Remove cached schema
        # Force refresh on next request
```

**Cache Key Format:**
```
{database_type}_{host}_{database_name}
```

**Cache Storage:**
- File-based storage in `cache/` directory
- JSON format for easy inspection
- Automatic cleanup of expired entries

## Query Generation Workflow

### Step-by-Step Process

1. **Receive Natural Language Query**
   - MCP client sends tool request
   - Extract query text and parameters

2. **Check Schema Cache**
   - Generate cache key from database info
   - Check if valid cached schema exists
   - If not, proceed to schema introspection

3. **Schema Introspection** (if needed)
   - Connect to database
   - Query metadata tables/collections
   - Extract table/collection names
   - Extract column/field definitions
   - Extract relationships/indexes
   - Cache the schema

4. **Build LLM Prompt**
   - Include natural language query
   - Add full schema context
   - Specify target query language
   - Add database-specific instructions
   - Include optimization hints

5. **Generate Query**
   - Call LLM API with prompt
   - Parse response
   - Extract query from response
   - Validate syntax (basic checks)

6. **Execute Query** (if requested)
   - Connect to database
   - Execute generated query
   - Fetch results
   - Format as JSON

7. **Return Response**
   - Include generated query
   - Include execution results (if executed)
   - Include metadata (execution time, row count)
   - Handle errors gracefully

## Error Handling

### Connection Errors
```python
try:
    connector.connect()
except ConnectionError as e:
    return {
        "error": "Database connection failed",
        "details": str(e),
        "suggestion": "Check credentials and network"
    }
```

### Schema Introspection Errors
```python
try:
    schema = connector.get_schema()
except PermissionError as e:
    return {
        "error": "Insufficient permissions",
        "details": str(e),
        "suggestion": "Grant schema read permissions"
    }
```

### Query Generation Errors
```python
try:
    query = llm_provider.generate_query(...)
except APIError as e:
    return {
        "error": "LLM API error",
        "details": str(e),
        "suggestion": "Check API key and quota"
    }
```

### Query Execution Errors
```python
try:
    results = connector.execute_query(query)
except QueryError as e:
    return {
        "error": "Query execution failed",
        "query": query,
        "details": str(e),
        "suggestion": "Review generated query syntax"
    }
```

## Performance Optimizations

### 1. Schema Caching
- Reduces database load
- Eliminates repeated introspection
- 80-90% latency reduction for cached schemas

### 2. Connection Pooling
```python
# Reuse database connections
connection_pool = {
    "mysql": SQLAlchemy pool,
    "mongodb": MongoClient with pooling,
    "neo4j": Driver with connection pool
}
```

### 3. Async Operations
```python
# Handle multiple requests concurrently
async def handle_request(request):
    schema = await get_schema_async()
    query = await generate_query_async()
    results = await execute_query_async()
    return results
```

### 4. Query Optimization
- Request optimized queries from LLM
- Use indexes when available
- Limit result sets
- Use projections to reduce data transfer

## Security Considerations

### 1. Credential Management
- Environment variables only
- No hardcoded credentials
- Support for IAM roles (AWS)
- Encrypted connections (SSL/TLS)

### 2. Query Validation
```python
def validate_query(query: str, query_type: str) -> bool:
    # Check for dangerous operations
    dangerous_keywords = ["DROP", "DELETE", "TRUNCATE"]
    if any(kw in query.upper() for kw in dangerous_keywords):
        raise SecurityError("Dangerous operation detected")
    return True
```

### 3. Rate Limiting
```python
# Limit LLM API calls
rate_limiter = RateLimiter(
    max_calls=100,
    time_window=3600  # 1 hour
)
```

### 4. Access Control
- Database-level permissions
- Read-only credentials recommended
- Network security (VPC, firewalls)
- API token authentication

## Testing Strategy

### Setup Testing (test_setup.py)

A comprehensive setup test script is included to verify configuration before running the server:

```bash
python test_setup.py           # Full connectivity test
python test_setup.py --quick    # Skip slow API calls
python test_setup.py --verbose  # Detailed output
```

**What it tests:**
- LLM provider connectivity (OpenAI/Anthropic)
- SQL databases (MySQL, PostgreSQL, Oracle, MS SQL, Snowflake)
- NoSQL databases (MongoDB, Redis, Cassandra, DynamoDB)
- Graph databases (Neo4j, ArangoDB, Neptune)
- GraphQL APIs (Generic, Saleor)
- Python package dependencies

**Benefits:**
- Catch configuration errors early
- Verify credentials before server start
- Identify missing packages
- Test network connectivity
- Validate environment setup

### Unit Tests
```python
# Test individual components
test_sql_connector()
test_nosql_connector()
test_schema_cache()
test_llm_provider()
```

### Integration Tests
```python
# Test end-to-end workflows
test_nl_to_sql_workflow()
test_schema_caching()
test_query_execution()
```

### Mock Testing
```python
# Mock external dependencies
mock_database_connection()
mock_llm_api_calls()
test_error_handling()
```

## Deployment

### Local Development
```bash
python server.py
```

### Production Deployment
```bash
# Use process manager
pm2 start server.py --name mcp-nl-to-data

# Or systemd service
systemctl start mcp-nl-to-data
```

### Docker Deployment
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "server.py"]
```

## Monitoring and Logging

### Logging Configuration
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp-server.log'),
        logging.StreamHandler()
    ]
)
```

### Metrics to Track
- Query generation time
- Query execution time
- Cache hit rate
- Error rate
- LLM API usage
- Database connection pool stats

## Future Enhancements

### Planned Features
1. Query result caching
2. Multi-query transactions
3. Query optimization feedback
4. Additional LLM providers (local models)
5. Web UI for testing
6. Query history and favorites
7. Real-time query streaming
8. Advanced error recovery

### Extensibility
- Plugin system for new databases
- Custom LLM provider integration
- Configurable caching strategies
- Query transformation pipelines

## Conclusion

The implementation follows best practices for modularity, security, and performance. The architecture allows for easy extension and maintenance while providing robust functionality for natural language to database query conversion.
