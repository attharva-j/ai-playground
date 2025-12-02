# Quick Reference - MCP Natural Language to Data Endpoints

## Common Commands

### Testing Your Setup

```bash
# Navigate to project directory
cd mcp-natural-language-to-data-endpoints

# Test all connections (recommended before first run)
python test_setup.py

# Quick test (skip slow API calls)
python test_setup.py --quick

# Verbose output for debugging
python test_setup.py --verbose
```

### Starting the Server

```bash
# Start the server (after testing)
python server.py
```

### Environment Setup

```bash
# Copy environment template
cp ../.env.example ../.env

# Edit environment file
# Windows: notepad ../.env
# Mac/Linux: nano ../.env
```

## Tool Reference

### 1. nl_to_sql

Convert natural language to SQL queries.

**Parameters:**
- `query` (string, required): Natural language question
- `database_type` (string, required): Database type (mysql, postgresql, oracle, mssql, snowflake, databricks)
- `execute` (boolean, optional): Execute the query (default: false)

**Example:**
```json
{
  "tool": "nl_to_sql",
  "arguments": {
    "query": "Show me the top 10 customers by total order value",
    "database_type": "postgresql",
    "execute": true
  }
}
```

**Response:**
```json
{
  "query": "SELECT customer_id, SUM(order_total) as total_value FROM orders GROUP BY customer_id ORDER BY total_value DESC LIMIT 10",
  "executed": true,
  "results": [...],
  "row_count": 10,
  "execution_time_ms": 45
}
```

### 2. nl_to_nosql

Convert natural language to NoSQL queries.

**Parameters:**
- `query` (string, required): Natural language question
- `database_type` (string, required): Database type (mongodb, cassandra, redis, dynamodb)
- `execute` (boolean, optional): Execute the query (default: false)

**Example:**
```json
{
  "tool": "nl_to_nosql",
  "arguments": {
    "query": "Find all users who signed up in the last 7 days",
    "database_type": "mongodb",
    "execute": true
  }
}
```

**Response:**
```json
{
  "query": "db.users.find({ signup_date: { $gte: new Date(Date.now() - 7*24*60*60*1000) } })",
  "executed": true,
  "results": [...],
  "document_count": 42
}
```

### 3. nl_to_cypher

Convert natural language to Cypher queries for graph databases.

**Parameters:**
- `query` (string, required): Natural language question
- `database_type` (string, required): Database type (neo4j, arangodb, neptune, cosmosdb)
- `execute` (boolean, optional): Execute the query (default: false)

**Example:**
```json
{
  "tool": "nl_to_cypher",
  "arguments": {
    "query": "Find all people who work at the same company as John Smith",
    "database_type": "neo4j",
    "execute": true
  }
}
```

**Response:**
```json
{
  "query": "MATCH (john:Person {name: 'John Smith'})-[:WORKS_AT]->(company:Company)<-[:WORKS_AT]-(colleague:Person) RETURN colleague.name",
  "executed": true,
  "results": [...],
  "node_count": 15
}
```

### 4. nl_to_graphql

Convert natural language to GraphQL queries.

**Parameters:**
- `query` (string, required): Natural language question
- `api_endpoint` (string, required): GraphQL API endpoint URL
- `execute` (boolean, optional): Execute the query (default: false)

**Example:**
```json
{
  "tool": "nl_to_graphql",
  "arguments": {
    "query": "Get all products with their prices and categories",
    "api_endpoint": "https://api.example.com/graphql",
    "execute": true
  }
}
```

**Response:**
```json
{
  "query": "query { products { id name price category { name } } }",
  "executed": true,
  "results": {...}
}
```

### 5. refresh_schema_cache

Manually refresh the cached schema for a database.

**Parameters:**
- `database_type` (string, required): Type of database
- `database_name` (string, required): Name of the database

**Example:**
```json
{
  "tool": "refresh_schema_cache",
  "arguments": {
    "database_type": "postgresql",
    "database_name": "production_db"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Schema cache refreshed successfully",
  "tables_found": 25,
  "cache_key": "postgresql_localhost_production_db"
}
```

## Common Query Patterns

### SQL Queries

**Aggregations:**
```
"Show me the total sales by region for the last quarter"
"Count the number of orders per customer"
"Calculate the average order value by product category"
```

**Filtering:**
```
"Find all customers who haven't placed an order in 90 days"
"Show me products with inventory below 10 units"
"List all orders with status 'pending' or 'processing'"
```

**Joins:**
```
"Show me all orders with customer names and product details"
"List employees with their department names and managers"
"Get all invoices with customer and payment information"
```

**Time-based:**
```
"Show me daily sales for the last 30 days"
"Find all users who registered this month"
"Get orders placed between January 1 and March 31"
```

### NoSQL Queries (MongoDB)

**Find Operations:**
```
"Find all users with premium subscription"
"Get all products in the 'Electronics' category"
"Show me documents where status is 'active'"
```

**Aggregations:**
```
"Group orders by customer and sum the totals"
"Count documents by category"
"Calculate average rating per product"
```

**Array Operations:**
```
"Find users with 'admin' in their roles array"
"Get products with tags containing 'sale'"
"Show documents where items array has more than 5 elements"
```

### Graph Queries (Cypher)

**Relationship Traversal:**
```
"Find all friends of friends of John"
"Show me people who work at companies in San Francisco"
"Get all products purchased by customers who also bought Product X"
```

**Pattern Matching:**
```
"Find the shortest path between Person A and Person B"
"Show me all circular relationships in the network"
"Get all nodes connected within 3 hops"
```

**Recommendations:**
```
"Recommend products based on similar users' purchases"
"Find people you might know based on mutual connections"
"Suggest companies based on employee connections"
```

### GraphQL Queries

**Simple Queries:**
```
"Get all users with their email addresses"
"Show me the first 10 products"
"Fetch the current user's profile"
```

**Nested Queries:**
```
"Get all orders with customer details and line items"
"Show me products with their categories and reviews"
"Fetch users with their posts and comments"
```

**Filtering:**
```
"Get products where price is less than 100"
"Show me users who joined after January 1, 2024"
"Find orders with status 'completed'"
```

## Environment Variables Quick Reference

### LLM Configuration
```env
MCP_LLM_PROVIDER=openai          # or 'anthropic'
MCP_LLM_MODEL=gpt-4              # or 'claude-3-sonnet-20240229'
OPENAI_API_KEY=sk-...            # Your OpenAI API key
ANTHROPIC_API_KEY=sk-ant-...     # Your Anthropic API key
```

### SQL Databases
```env
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=password
MYSQL_DATABASE=mydb

# PostgreSQL
POSTGRESQL_HOST=localhost
POSTGRESQL_PORT=5432
POSTGRESQL_USER=postgres
POSTGRESQL_PASSWORD=password
POSTGRESQL_DATABASE=mydb

# Snowflake
SNOWFLAKE_ACCOUNT=xy12345.us-east-1
SNOWFLAKE_USER=user
SNOWFLAKE_PASSWORD=password
SNOWFLAKE_DATABASE=DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

### NoSQL Databases
```env
# MongoDB
MONGODB_URI=mongodb://user:pass@localhost:27017
MONGODB_DATABASE=mydb

# DynamoDB
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

### Graph Databases
```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Neptune
NEPTUNE_ENDPOINT=my-cluster.cluster-xxx.us-east-1.neptune.amazonaws.com
NEPTUNE_PORT=8182
```

### GraphQL
```env
GRAPHQL_API_TOKEN=your_token
SALEOR_API_TOKEN=your_saleor_token
```

## Troubleshooting Quick Fixes

### Run Setup Test First
```bash
# Always start with the test script
python test_setup.py

# This will identify:
# - Missing credentials
# - Connection issues
# - Package problems
# - Configuration errors
```

### Schema Not Loading
```bash
# Test database connection first
python test_setup.py

# Check database connection
# Verify credentials in .env file
# Test with database client tool

# Force schema refresh
# Use refresh_schema_cache tool
```

### Query Generation Fails
```bash
# Verify LLM API key
echo $OPENAI_API_KEY

# Check API quota/billing
# Try simpler query first
```

### Execution Errors
```bash
# Test generated query manually
# Check database permissions
# Review query syntax
# Enable debug logging
```

### Connection Timeouts
```bash
# Check firewall rules
# Verify security groups (cloud)
# Test network connectivity
# Increase timeout values
```

## Performance Tips

1. **Use Schema Caching**: Schemas are cached for 24 hours by default
2. **Limit Result Sets**: Add limits to queries for faster responses
3. **Use Indexes**: Ensure databases have proper indexes
4. **Batch Operations**: Group multiple queries when possible
5. **Monitor API Usage**: Track LLM API calls to manage costs

## Best Practices

1. **Run Setup Tests**: Always run `python test_setup.py` after configuration changes
2. **Start with Dry Runs**: Use `execute: false` to test queries first
3. **Use Read-Only Credentials**: Especially for production databases
4. **Monitor Costs**: Track LLM API usage
5. **Refresh Schemas**: After database structure changes
6. **Test Queries**: Validate generated queries before execution
7. **Use Specific Queries**: More specific questions generate better queries
8. **Review Results**: Always verify query results for accuracy
9. **Quick Tests**: Use `--quick` flag for frequent testing to save API credits

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "Database connection failed" | Invalid credentials or network issue | Check .env file and connectivity |
| "Schema introspection failed" | Insufficient permissions | Grant schema read permissions |
| "LLM API error" | Invalid API key or quota exceeded | Verify API key and billing |
| "Query execution failed" | Invalid query syntax | Review generated query |
| "Cache read error" | Corrupted cache file | Delete cache and refresh |

## Additional Resources

- [GET_STARTED.md](GET_STARTED.md) - Quick start guide
- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Detailed setup instructions
- [WORKFLOW.md](WORKFLOW.md) - Query transformation and routing workflow
- [IMPLEMENTATION.md](IMPLEMENTATION.md) - Technical architecture
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Project overview
