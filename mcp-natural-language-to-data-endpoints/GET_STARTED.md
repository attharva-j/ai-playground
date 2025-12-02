# Getting Started with MCP Natural Language to Data Endpoints

## Overview

The MCP Natural Language to Data Endpoints server is a powerful tool that converts natural language queries into database-specific queries (SQL, NoSQL, Cypher, GraphQL) and executes them across multiple database platforms.

## Quick Start

### 1. Installation

```bash
# Navigate to the project directory
cd mcp-natural-language-to-data-endpoints

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy the `.env.example` file from the root directory and configure your database connections:

```bash
cp ../.env.example ../.env
```

Edit the `.env` file and add your credentials for:
- LLM provider (OpenAI or Anthropic)
- Database connections you want to use

### 3. Test Your Setup (Recommended)

Before running the server, test your configuration:

```bash
# Test all configured connections
python test_setup.py
```

This will verify:
- LLM provider connectivity (OpenAI/Anthropic)
- Database connections (SQL, NoSQL, Graph, GraphQL)
- Required Python packages
- Configuration completeness

**Test Options:**
```bash
python test_setup.py           # Full test
python test_setup.py --quick    # Skip slow API tests
python test_setup.py --verbose  # Detailed output
```

### 4. Running the Server

```bash
# Run the MCP server
python server.py
```

The server will start and listen for MCP protocol messages via stdio.

### 5. Basic Usage

The server exposes four main tools:

#### Natural Language to SQL
```json
{
  "tool": "nl_to_sql",
  "arguments": {
    "query": "Show me all customers who made purchases in the last 30 days",
    "database_type": "postgresql",
    "execute": false
  }
}
```

#### Natural Language to NoSQL
```json
{
  "tool": "nl_to_nosql",
  "arguments": {
    "query": "Find all users with premium subscription",
    "database_type": "mongodb",
    "execute": false
  }
}
```

#### Natural Language to Cypher
```json
{
  "tool": "nl_to_cypher",
  "arguments": {
    "query": "Find all friends of John who work at the same company",
    "database_type": "neo4j",
    "execute": false
  }
}
```

#### Natural Language to GraphQL
```json
{
  "tool": "nl_to_graphql",
  "arguments": {
    "query": "Get all products with their categories and prices",
    "api_endpoint": "https://api.example.com/graphql",
    "execute": false
  }
}
```

## Key Features

1. **Multi-Database Support**: Connect to 20+ database types including SQL, NoSQL, Graph, and GraphQL
2. **Automatic Schema Caching**: Schemas are automatically fetched and cached for faster query generation
3. **Pluggable LLM**: Choose between OpenAI or Anthropic for query generation
4. **Query Execution**: Optionally execute generated queries and get results
5. **Schema Refresh**: Manually refresh cached schemas when database structure changes

## Next Steps

- Read the [Setup Guide](SETUP_GUIDE.md) for detailed configuration instructions
- Check the [Quick Reference](QUICK_REFERENCE.md) for common operations
- Review the [Implementation](IMPLEMENTATION.md) for technical details
- See [Project Summary](PROJECT_SUMMARY.md) for architecture overview

## Supported Databases

### SQL Databases
- MySQL (Local/Remote)
- PostgreSQL (Local/Remote)
- Oracle Database (Local/Remote)
- MS-SQL Server (Local/Remote)
- Snowflake
- Databricks
- AWS RDS
- GCP Cloud SQL
- Azure SQL Database

### NoSQL Databases
- MongoDB
- Apache Cassandra
- Redis
- AWS DynamoDB

### Graph Databases
- Neo4j
- ArangoDB
- GraphDB (RDF)
- Amazon Neptune
- Azure CosmosDB (Gremlin API)

### GraphQL APIs
- Generic GraphQL endpoints
- Saleor API
- Custom GraphQL implementations

## Troubleshooting

### Always Start with the Test Script

Before troubleshooting, run the test script to identify issues:

```bash
python test_setup.py
```

This will immediately show you:
- Which connections are working
- Which connections are failing
- Missing packages
- Configuration errors

### Schema Not Loading
If schemas aren't loading, check:
1. Run `python test_setup.py` to verify database connectivity
2. Database credentials in `.env` file
3. Network connectivity to database
4. Database permissions for schema introspection

### Query Generation Issues
If queries aren't generating correctly:
1. Run `python test_setup.py` to verify LLM provider
2. Verify LLM API key is set
3. Check that schema was cached successfully
4. Try refreshing the schema cache

### Execution Errors
If query execution fails:
1. Run `python test_setup.py` to verify database connection
2. Test the generated query manually first
3. Verify database permissions
4. Check query syntax for the specific database dialect

### Connection Timeouts
If you're experiencing timeouts:
1. Run `python test_setup.py` to isolate the issue
2. Check firewall rules
3. Verify security groups (for cloud databases)
4. Test with database client tools

## Support

For issues or questions:
1. **Run the test script first**: `python test_setup.py`
2. Check the documentation files in this folder
3. Review error messages in the console
4. Verify all environment variables are set correctly
