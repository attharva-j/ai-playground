# MCP Natural Language to Data Endpoints

A Model Context Protocol (MCP) server that converts natural language queries into database-specific queries across 20+ database types including SQL, NoSQL, Graph databases, and GraphQL APIs.

## Overview

This MCP server enables you to query any database using plain English. Simply ask a question in natural language, and the system automatically generates the appropriate query syntax (SQL, MongoDB, Cypher, GraphQL, etc.), executes it, and returns formatted results.

**Example:**
```
"Show me the top 10 customers by revenue in the last quarter"
→ Generates optimized SQL query
→ Executes against your database
→ Returns structured results
```

## Key Features

- **20+ Database Support**: SQL (MySQL, PostgreSQL, Oracle, Snowflake), NoSQL (MongoDB, Redis, DynamoDB), Graph (Neo4j, Neptune), GraphQL
- **Intelligent Query Generation**: Powered by OpenAI GPT-4 or Anthropic Claude
- **Schema Caching**: Automatic schema introspection with 24-hour caching for performance
- **Flexible Execution**: Generate queries without execution (dry-run) or execute and get results
- **MCP Protocol**: Seamless integration with Claude Desktop and other MCP clients

## Quick Start

### 1. Install Dependencies

```bash
cd mcp-natural-language-to-data-endpoints
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp ../.env.example ../.env

# Edit .env and add your credentials
# - LLM API key (OpenAI or Anthropic)
# - Database connection details
```

### 3. Test Your Setup (Recommended)

```bash
# Test all configured connections
python test_setup.py

# Quick test (skip slow API calls)
python test_setup.py --quick
```

### 4. Run the Server

```bash
python server.py
```

### 5. Configure MCP Client

Add to your MCP client configuration (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "nl-to-data": {
      "command": "python",
      "args": ["C:/path/to/mcp-natural-language-to-data-endpoints/server.py"]
    }
  }
}
```


## Supported Databases

### SQL Databases
- MySQL / MariaDB (Local & Remote)
- PostgreSQL (Local & Remote)
- Oracle Database
- Microsoft SQL Server
- Snowflake
- Databricks
- AWS RDS (MySQL, PostgreSQL)
- GCP Cloud SQL
- Azure SQL Database

### NoSQL Databases
- MongoDB
- Apache Cassandra
- Redis
- AWS DynamoDB

### Graph Databases
- Neo4j (Cypher)
- ArangoDB (AQL)
- GraphDB (SPARQL/RDF)
- Amazon Neptune (Gremlin)
- Azure CosmosDB (Gremlin API)

### GraphQL APIs
- Generic GraphQL endpoints
- Saleor Commerce API
- Custom GraphQL implementations

## Usage Examples

### SQL Query Generation

```json
{
  "tool": "nl_to_sql",
  "arguments": {
    "query": "Find all orders placed in the last 30 days with total value over $1000",
    "database_type": "postgresql",
    "execute": true
  }
}
```

**Response:**
```json
{
  "query": "SELECT * FROM orders WHERE order_date >= NOW() - INTERVAL '30 days' AND total_amount > 1000",
  "executed": true,
  "results": [...],
  "row_count": 42
}
```

### MongoDB Query Generation

```json
{
  "tool": "nl_to_nosql",
  "arguments": {
    "query": "Get all users with premium subscription who logged in this week",
    "database_type": "mongodb",
    "execute": true
  }
}
```

### Neo4j Graph Query

```json
{
  "tool": "nl_to_cypher",
  "arguments": {
    "query": "Find all friends of John who work at the same company",
    "database_type": "neo4j",
    "execute": true
  }
}
```

### GraphQL Query

```json
{
  "tool": "nl_to_graphql",
  "arguments": {
    "query": "Get all products with their categories, prices, and inventory status",
    "api_endpoint": "https://api.example.com/graphql",
    "execute": true
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `nl_to_sql` | Convert natural language to SQL queries |
| `nl_to_nosql` | Convert natural language to NoSQL queries (MongoDB, Cassandra, etc.) |
| `nl_to_cypher` | Convert natural language to Cypher/graph queries |
| `nl_to_graphql` | Convert natural language to GraphQL queries |
| `refresh_schema_cache` | Manually refresh cached database schemas |


## Configuration

### Environment Variables

**LLM Provider:**
```env
MCP_LLM_PROVIDER=openai          # or 'anthropic'
MCP_LLM_MODEL=gpt-4              # or 'claude-3-sonnet-20240229'
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Database Examples:**
```env
# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=mydb

# PostgreSQL
POSTGRESQL_HOST=localhost
POSTGRESQL_PORT=5432
POSTGRESQL_USER=postgres
POSTGRESQL_PASSWORD=your_password
POSTGRESQL_DATABASE=mydb

# MongoDB
MONGODB_URI=mongodb://user:pass@localhost:27017
MONGODB_DATABASE=mydb

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Snowflake
SNOWFLAKE_ACCOUNT=xy12345.us-east-1
SNOWFLAKE_USER=user
SNOWFLAKE_PASSWORD=password
SNOWFLAKE_DATABASE=DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete configuration details.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP Client                           │
│                   (Claude Desktop, etc.)                    │
└────────────────────────┬────────────────────────────────────┘
                         │ MCP Protocol (stdio)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   MCP Server (server.py)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Tool Handlers                                       │   │
│  │  • nl_to_sql    • nl_to_cypher                       │   │
│  │  • nl_to_nosql  • nl_to_graphql                      │   │
│  └──────────────────────────────────────────────────────┘   │
└────────┬──────────────────┬──────────────────┬──────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─────────────────┐ ┌──────────────┐ ┌─────────────────┐
│   Connectors    │ │ LLM Provider │ │  Schema Cache   │
│                 │ │              │ │                 │
│ • SQL           │ │ • OpenAI     │ │ • File-based    │
│ • NoSQL         │ │ • Anthropic  │ │ • 24h TTL       │
│ • Graph         │ │              │ │                 │
│ • GraphQL       │ │              │ │                 │
└────────┬────────┘ └──────────────┘ └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database Systems                         │
│  SQL • NoSQL • Graph • GraphQL                              │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
mcp-natural-language-to-data-endpoints/
├── server.py                    # MCP server entry point
├── requirements.txt             # Python dependencies
├── connectors/                  # Database connectors
│   ├── sql_connector.py        # SQL databases
│   ├── nosql_connector.py      # NoSQL databases
│   ├── graph_connector.py      # Graph databases
│   └── graphql_connector.py    # GraphQL APIs
├── llm/                        # LLM integration
│   └── provider.py             # OpenAI/Anthropic provider
├── cache/                      # Schema caching
│   └── schema_cache.py         # Cache management
└── docs/                       # Documentation
    ├── README.md               # This file
    ├── GET_STARTED.md          # Quick start guide
    ├── SETUP_GUIDE.md          # Detailed setup
    ├── IMPLEMENTATION.md       # Technical details
    ├── QUICK_REFERENCE.md      # Command reference
    └── PROJECT_SUMMARY.md      # Project overview
```


## How It Works

1. **Natural Language Input**: User asks a question in plain English
2. **Schema Retrieval**: System fetches database schema (cached for 24 hours)
3. **Query Generation**: LLM generates optimized database-specific query
4. **Execution** (optional): Query is executed against the database
5. **Results**: Formatted results returned to the user

### Query Generation Process

```
Natural Language Query
        ↓
Schema Cache Check
        ↓
Schema Introspection (if needed)
        ↓
LLM Prompt Building (with schema context)
        ↓
Query Generation (OpenAI/Anthropic)
        ↓
Query Validation
        ↓
Execution (if requested)
        ↓
Formatted Results
```

## Performance

- **Schema Caching**: 80-90% latency reduction for repeated queries
- **Connection Pooling**: Efficient database connection management
- **Async Operations**: Concurrent request handling
- **Optimized Queries**: LLM generates efficient, indexed queries

## Security

- **Environment Variables**: All credentials stored securely in `.env`
- **Read-Only Recommended**: Use read-only database credentials
- **Query Validation**: Basic validation before execution
- **SSL/TLS Support**: Encrypted connections to remote databases
- **No Credential Logging**: Sensitive data never logged

## Testing Your Setup

Before running the server, it's highly recommended to test your configuration:

```bash
# Run the setup test script
python test_setup.py
```

This script will:
- ✓ Verify LLM provider configuration and connectivity
- ✓ Test all configured database connections
- ✓ Check for missing Python packages
- ✓ Provide detailed error messages for failed connections
- ✓ Give you a summary of what's working

**Test Options:**
```bash
python test_setup.py           # Full test with API calls
python test_setup.py --quick    # Skip slow API tests
python test_setup.py --verbose  # Detailed output
```

## Troubleshooting

### Common Issues

**Schema Not Loading**
```bash
# Run the test script first
python test_setup.py

# Check database credentials
# Verify network connectivity
# Ensure schema read permissions
# Try manual schema refresh
```

**Query Generation Fails**
```bash
# Verify LLM API key
# Check API quota/billing
# Review schema cache validity
```

**Connection Timeouts**
```bash
# Check firewall rules
# Verify security groups (cloud)
# Test with database client
```

See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for detailed troubleshooting.

## Documentation

- **[GET_STARTED.md](GET_STARTED.md)** - Quick start guide with examples
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup for all databases
- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** - Technical architecture
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command reference and tips
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Complete project overview
- **[PROJECT_STRUCTURE.txt](PROJECT_STRUCTURE.txt)** - File organization

## Testing Script

The `test_setup.py` script is your best friend for troubleshooting:

**What it does:**
- ✓ Tests LLM provider connectivity (OpenAI/Anthropic)
- ✓ Tests all configured database connections
- ✓ Checks for missing Python packages
- ✓ Provides detailed error messages
- ✓ Gives pass/fail summary

**When to use:**
- After initial setup
- Before starting the server
- After changing .env configuration
- When troubleshooting connection issues
- After database infrastructure changes

**How to run:**
```bash
python test_setup.py           # Full test
python test_setup.py --quick    # Skip slow API calls
python test_setup.py --verbose  # Detailed output
```

## Requirements

- Python 3.9 or higher
- OpenAI or Anthropic API key
- Access to at least one database system
- Network connectivity to databases

## Use Cases

- **Data Analysis**: Query production databases without SQL knowledge
- **Business Intelligence**: Ad-hoc reporting and analytics
- **Graph Exploration**: Navigate complex relationships in graph databases
- **API Integration**: Query GraphQL APIs with natural language
- **Multi-Database**: Unified interface for diverse database systems

## Limitations

- Single-query operations (no transactions)
- 24-hour schema cache TTL (configurable)
- No query result caching (yet)
- Read operations recommended

## Future Enhancements

- Query result caching
- Multi-query transactions
- Query performance analytics
- Local LLM support
- Web UI for testing
- Query history and favorites

## Contributing

This project is designed to be extensible:

- Add new database connectors in `connectors/`
- Integrate additional LLM providers in `llm/`
- Implement custom caching strategies
- Add query optimization rules

## License

Open-source project for enterprise and personal use.

## Support

For issues or questions:
1. Review the documentation files
2. Check environment variable configuration
3. Verify database connectivity
4. Review error messages in console output

## Example Queries

**SQL:**
- "Show me all customers who haven't ordered in 90 days"
- "Calculate total revenue by product category this year"
- "Find the top 5 best-selling products"

**MongoDB:**
- "Get all users with premium subscription"
- "Find documents where status is active and created this month"
- "Count orders grouped by customer"

**Neo4j:**
- "Find all friends of friends of John"
- "Show me the shortest path between Person A and Person B"
- "Get all products purchased by similar customers"

**GraphQL:**
- "Get all products with their categories and prices"
- "Fetch user profile with posts and comments"
- "Show me orders with customer details"

---

**Ready to get started?** Check out [GET_STARTED.md](GET_STARTED.md) for a quick setup guide!
