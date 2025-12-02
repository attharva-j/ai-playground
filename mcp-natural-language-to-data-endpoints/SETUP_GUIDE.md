# Setup Guide - MCP Natural Language to Data Endpoints

## Prerequisites

- Python 3.9 or higher
- pip package manager
- Access to at least one database system
- OpenAI or Anthropic API key

## Installation Steps

### 1. Install Python Dependencies

```bash
cd mcp-natural-language-to-data-endpoints
pip install -r requirements.txt
```

### 2. Database-Specific Setup

Depending on which databases you plan to use, you may need additional system-level dependencies:

#### Oracle Database
```bash
# Download and install Oracle Instant Client
# https://www.oracle.com/database/technologies/instant-client/downloads.html
```

#### MS-SQL Server
```bash
# Install ODBC Driver 17 for SQL Server
# Windows: Download from Microsoft
# Linux: Follow Microsoft's installation guide
```

#### Graph Databases
For Gremlin-based databases (Neptune, CosmosDB), ensure you have network access to the endpoints.

### 3. Environment Configuration

#### Step 3.1: Copy Environment Template

```bash
cp ../.env.example ../.env
```

#### Step 3.2: Configure LLM Provider

Choose your LLM provider and set the appropriate variables:

**For OpenAI:**
```env
MCP_LLM_PROVIDER=openai
MCP_LLM_MODEL=gpt-4
OPENAI_API_KEY=sk-proj-your-key-here
```

**For Anthropic:**
```env
MCP_LLM_PROVIDER=anthropic
MCP_LLM_MODEL=claude-3-sonnet-20240229
ANTHROPIC_API_KEY=your-anthropic-key-here
```

#### Step 3.3: Configure Database Connections

Configure only the databases you plan to use:

**MySQL Example:**
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_secure_password
MYSQL_DATABASE=myapp_db
```

**PostgreSQL Example:**
```env
POSTGRESQL_HOST=db.example.com
POSTGRESQL_PORT=5432
POSTGRESQL_USER=dbuser
POSTGRESQL_PASSWORD=your_secure_password
POSTGRESQL_DATABASE=production_db
```

**MongoDB Example:**
```env
MONGODB_URI=mongodb://user:password@localhost:27017
MONGODB_DATABASE=myapp
```

**Neo4j Example:**
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
```

**Snowflake Example:**
```env
SNOWFLAKE_ACCOUNT=xy12345.us-east-1
SNOWFLAKE_USER=analytics_user
SNOWFLAKE_PASSWORD=your_secure_password
SNOWFLAKE_DATABASE=ANALYTICS
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

**AWS DynamoDB Example:**
```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**GraphQL API Example:**
```env
GRAPHQL_API_TOKEN=your_api_token
SALEOR_API_TOKEN=your_saleor_token
```

### 4. Verify Installation

Create a test script to verify your setup:

```python
# test_connection.py
import os
from dotenv import load_dotenv

load_dotenv()

# Test LLM configuration
llm_provider = os.getenv("MCP_LLM_PROVIDER")
print(f"LLM Provider: {llm_provider}")

# Test database configurations
if os.getenv("MYSQL_HOST"):
    print("✓ MySQL configured")

if os.getenv("POSTGRESQL_HOST"):
    print("✓ PostgreSQL configured")

if os.getenv("MONGODB_URI"):
    print("✓ MongoDB configured")

if os.getenv("NEO4J_URI"):
    print("✓ Neo4j configured")

print("\nSetup verification complete!")
```

Run the test:
```bash
python test_connection.py
```

### 5. Configure MCP Client

To use this server with an MCP client (like Claude Desktop), add it to your MCP configuration:

**For Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):**

```json
{
  "mcpServers": {
    "nl-to-data": {
      "command": "python",
      "args": ["/path/to/mcp-natural-language-to-data-endpoints/server.py"],
      "env": {
        "PYTHONPATH": "/path/to/project/root"
      }
    }
  }
}
```

### 6. Test Your Setup

**IMPORTANT:** Before running the server, test your configuration:

```bash
python test_setup.py
```

The test script will:
- ✓ Verify LLM provider (OpenAI/Anthropic) connectivity
- ✓ Test all configured database connections
- ✓ Check for missing Python packages
- ✓ Provide detailed error messages
- ✓ Give you a pass/fail summary

**Test Options:**
```bash
python test_setup.py           # Full test with API calls
python test_setup.py --quick    # Skip slow tests (faster)
python test_setup.py --verbose  # Detailed output
```

**Example Output:**
```
╔════════════════════════════════════════════════════════════╗
║  MCP Natural Language to Data Endpoints - Setup Test      ║
╚════════════════════════════════════════════════════════════╝

============================================================
                    Testing LLM Providers
============================================================

ℹ Configured Provider: openai
ℹ Configured Model: gpt-4
✓ OpenAI API connection successful (Model: gpt-4)

============================================================
                    Testing SQL Databases
============================================================

✓ PostgreSQL connection successful (localhost)
✓ MySQL connection successful (localhost)

============================================================
                        Test Summary
============================================================

LLM:
✓ OpenAI: Connected

SQL:
✓ PostgreSQL: Connected
✓ MySQL: Connected

============================================================
Total Tests: 3
Passed: 3
Failed: 0
============================================================

✓ All configured connections are working! ✨
ℹ You can now run the MCP server with: python server.py
```

### 7. Start the Server

Once all tests pass, start the server:

```bash
python server.py
```

The server should start without errors. Press Ctrl+C to stop.

## Cloud Database Setup

### AWS RDS (MySQL/PostgreSQL)

1. Create an RDS instance in AWS Console
2. Configure security groups to allow your IP
3. Use the endpoint as the host in your `.env` file
4. Use standard MySQL/PostgreSQL configuration

### Snowflake

1. Create a Snowflake account
2. Create a warehouse and database
3. Generate user credentials
4. Use the account identifier format: `account.region`

### Databricks

1. Create a Databricks workspace
2. Create a SQL warehouse
3. Get the HTTP path from warehouse details
4. Generate a personal access token
5. Configure in `.env` file

### Amazon Neptune

1. Create a Neptune cluster in AWS
2. Configure VPC and security groups
3. Use the cluster endpoint
4. Ensure your application has network access

### Azure CosmosDB (Gremlin)

1. Create a CosmosDB account with Gremlin API
2. Create a database and graph
3. Get the Gremlin endpoint and primary key
4. Configure in `.env` file

## Security Best Practices

1. **Never commit `.env` file** - It contains sensitive credentials
2. **Use environment-specific files** - `.env.development`, `.env.production`
3. **Rotate credentials regularly** - Especially for production databases
4. **Use read-only credentials** - When possible, for query-only operations
5. **Enable SSL/TLS** - For all remote database connections
6. **Use IAM roles** - For AWS services instead of access keys
7. **Implement rate limiting** - To prevent abuse of LLM APIs
8. **Monitor API usage** - Track LLM API costs

## Testing Best Practices

### When to Run Tests

1. **After initial setup** - Verify everything is configured correctly
2. **Before starting the server** - Catch issues early
3. **After changing .env** - Confirm new credentials work
4. **After database changes** - Ensure connectivity is maintained
5. **When troubleshooting** - Identify specific connection issues

### Quick Test vs Full Test

**Quick Test** (`--quick` flag):
- Skips actual LLM API calls (saves API credits)
- Only verifies API keys are configured
- Faster execution
- Good for frequent checks

**Full Test** (default):
- Makes actual API calls to LLM providers
- Verifies complete end-to-end connectivity
- More thorough but uses API credits
- Recommended before production use

## Troubleshooting

### Using test_setup.py for Debugging

The test script is your first line of defense for troubleshooting:

```bash
# Run full diagnostic
python test_setup.py

# Check specific issues with verbose output
python test_setup.py --verbose
```

### Import Errors

If you get import errors:
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt --upgrade

# Check Python version
python --version  # Should be 3.9+
```

### Connection Timeouts

For remote databases:
1. Check firewall rules
2. Verify security group settings
3. Test connectivity with database client tools
4. Increase timeout values if needed

### Schema Introspection Fails

1. Verify database user has schema read permissions
2. Check if database has tables/collections
3. Review database-specific logs
4. Try manual schema queries

### LLM API Errors

1. Verify API key is correct
2. Check API quota and billing
3. Test API key with curl/Postman
4. Review rate limits

## Next Steps

- Read [Workflow](WORKFLOW.md) to understand the query transformation process
- Check [Implementation](IMPLEMENTATION.md) for technical architecture details
- Review [Quick Reference](QUICK_REFERENCE.md) for common commands
- See [Project Summary](PROJECT_SUMMARY.md) for complete overview
