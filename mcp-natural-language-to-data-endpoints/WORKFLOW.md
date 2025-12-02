# Workflow - MCP Natural Language to Data Endpoints

This document explains how natural language queries are transformed into database-specific queries and executed across different database types.

## Table of Contents

1. [Overview](#overview)
2. [High-Level Workflow](#high-level-workflow)
3. [Detailed Step-by-Step Process](#detailed-step-by-step-process)
4. [Query Type Routing](#query-type-routing)
5. [Database-Specific Workflows](#database-specific-workflows)
6. [Schema Caching Mechanism](#schema-caching-mechanism)
7. [Error Handling Flow](#error-handling-flow)
8. [Example Workflows](#example-workflows)

## Overview

The MCP Natural Language to Data Endpoints server follows a multi-stage pipeline to convert natural language into executable database queries:

```
Natural Language → Tool Selection → Schema Retrieval → Query Generation → Execution → Results
```

Each stage is designed to be modular, allowing for easy extension and maintenance.

## High-Level Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Client                              │
│                    (Claude Desktop, etc.)                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ 1. Natural Language Query
                             │    + Database Type
                             │    + Execute Flag
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Server                               │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  2. Tool Router                                        │     │
│  │     • nl_to_sql → SQL Handler                          │     │
│  │     • nl_to_nosql → NoSQL Handler                      │     │
│  │     • nl_to_cypher → Graph Handler                     │     │
│  │     • nl_to_graphql → GraphQL Handler                  │     │
│  └────────────────────────────────────────────────────────┘     │
│                             │                                   │
│                             ▼                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  3. Schema Manager                                     │     │ 
│  │     • Check Cache                                      │     │
│  │     • Load from Cache OR Fetch from Database           │     │
│  └────────────────────────────────────────────────────────┘     │
│                             │                                   │
│                             ▼                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  4. LLM Provider                                       │     │
│  │     • Build Context-Aware Prompt                       │     │
│  │     • Include Schema Information                       │     │
│  │     • Call LLM API (OpenAI/Anthropic)                  │     │
│  │     • Parse Generated Query                            │     │
│  └────────────────────────────────────────────────────────┘     │
│                             │                                   │
│                             ▼                                   │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  5. Query Executor (if execute=true)                   │     │
│  │     • Validate Query                                   │     │
│  │     • Execute via Connector                            │     │
│  │     • Format Results                                   │     │
│  └────────────────────────────────────────────────────────┘     │
│                             │                                   │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                              │ 6. Return Response
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Client                              │
│  Response:                                                      │
│  • Generated Query                                              │
│  • Execution Results (if executed)                              │
│  • Metadata (row count, execution time)                         │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Step-by-Step Process

### Step 1: Request Reception

**Input from MCP Client:**
```json
{
  "tool": "nl_to_sql",
  "arguments": {
    "query": "Show me all customers who made purchases in the last 30 days",
    "database_type": "postgresql",
    "execute": true
  }
}
```

**Server Actions:**
1. Parse incoming MCP request
2. Extract tool name and arguments
3. Validate required parameters
4. Route to appropriate handler

### Step 2: Tool Routing

The server routes the request based on the tool name:

```python
# Pseudo-code for routing logic
if tool == "nl_to_sql":
    handler = sql_handler
    connector_type = SQLConnector
elif tool == "nl_to_nosql":
    handler = nosql_handler
    connector_type = NoSQLConnector
elif tool == "nl_to_cypher":
    handler = graph_handler
    connector_type = GraphConnector
elif tool == "nl_to_graphql":
    handler = graphql_handler
    connector_type = GraphQLConnector
```

**Routing Decision Tree:**
```
Request
  │
  ├─ nl_to_sql ────────────→ SQL Handler ────→ SQLConnector
  │                                              ├─ MySQL
  │                                              ├─ PostgreSQL
  │                                              ├─ Oracle
  │                                              ├─ MS-SQL
  │                                              └─ Snowflake
  │
  ├─ nl_to_nosql ──────────→ NoSQL Handler ───→ NoSQLConnector
  │                                              ├─ MongoDB
  │                                              ├─ Redis
  │                                              ├─ Cassandra
  │                                              └─ DynamoDB
  │
  ├─ nl_to_cypher ─────────→ Graph Handler ───→ GraphConnector
  │                                              ├─ Neo4j
  │                                              ├─ ArangoDB
  │                                              └─ Neptune
  │
  └─ nl_to_graphql ────────→ GraphQL Handler ─→ GraphQLConnector
                                                 ├─ Generic API
                                                 └─ Saleor API
```


### Step 3: Schema Retrieval

**Schema Cache Check:**
```python
# Generate cache key
cache_key = f"{database_type}_{host}_{database_name}"

# Check if schema exists in cache
cached_schema = schema_cache.get(cache_key)

if cached_schema and not expired:
    schema = cached_schema
else:
    # Fetch schema from database
    schema = connector.get_schema()
    # Cache for future use
    schema_cache.set(cache_key, schema)
```

**Schema Retrieval Flow:**
```
┌─────────────────────────────────────────────────────────────┐
│  Schema Manager                                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Check Cache          │
            │  Key: db_host_name    │
            └───────┬───────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐      ┌────────────────┐
│ Cache Hit     │      │ Cache Miss     │
│ (Valid TTL)   │      │ (or Expired)   │
└───────┬───────┘      └────────┬───────┘
        │                       │
        │                       ▼
        │              ┌─────────────────────┐
        │              │ Connect to Database │
        │              └─────────┬───────────┘
        │                        │
        │                        ▼
        │              ┌─────────────────────┐
        │              │ Introspect Schema   │
        │              │ • Tables/Collections│
        │              │ • Columns/Fields    │
        │              │ • Relationships     │
        │              │ • Indexes           │
        │              └─────────┬───────────┘
        │                        │
        │                        ▼
        │              ┌─────────────────────┐
        │              │ Cache Schema        │
        │              │ TTL: 24 hours       │
        │              └─────────┬───────────┘
        │                        │
        └────────────────────────┘
                        │
                        ▼
                ┌───────────────┐
                │ Return Schema │
                └───────────────┘
```

**Schema Format Examples:**

**SQL Schema:**
```json
{
  "tables": [
    {
      "name": "customers",
      "columns": [
        {"name": "id", "type": "integer", "primary_key": true},
        {"name": "name", "type": "varchar(255)"},
        {"name": "email", "type": "varchar(255)"},
        {"name": "created_at", "type": "timestamp"}
      ]
    },
    {
      "name": "orders",
      "columns": [
        {"name": "id", "type": "integer", "primary_key": true},
        {"name": "customer_id", "type": "integer", "foreign_key": "customers.id"},
        {"name": "total_amount", "type": "decimal(10,2)"},
        {"name": "order_date", "type": "timestamp"}
      ]
    }
  ]
}
```

**MongoDB Schema:**
```json
{
  "collections": [
    {
      "name": "users",
      "sample_document": {
        "_id": "ObjectId",
        "name": "string",
        "email": "string",
        "subscription": {
          "type": "string",
          "status": "string",
          "expires_at": "date"
        },
        "created_at": "date"
      }
    }
  ]
}
```

**Neo4j Schema:**
```json
{
  "node_labels": ["Person", "Company", "Product"],
  "relationship_types": ["WORKS_AT", "PURCHASED", "FRIENDS_WITH"],
  "properties": {
    "Person": ["name", "email", "age"],
    "Company": ["name", "industry", "location"],
    "WORKS_AT": ["since", "position"]
  }
}
```

### Step 4: Query Generation

**LLM Prompt Construction:**
```python
prompt = f"""
You are a {database_type} query expert. Generate a query based on the following:

Natural Language Request:
{user_query}

Database Schema:
{schema_json}

Requirements:
- Generate ONLY the query, no explanations
- Use proper {database_type} syntax
- Optimize for performance
- Use appropriate indexes when available
- Handle edge cases (NULL values, empty results)

Query:
"""
```

**LLM Provider Flow:**
```
┌─────────────────────────────────────────────────────────────┐
│  LLM Provider                                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Build Prompt         │
            │  • User Query         │
            │  • Schema Context     │
            │  • Database Type      │
            │  • Best Practices     │
            └───────┬───────────────┘
                    │
                    ▼
            ┌───────────────────────┐
            │  Select Provider      │
            └───────┬───────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐      ┌────────────────┐
│ OpenAI        │      │ Anthropic      │
│ GPT-4         │      │ Claude 3       │
└───────┬───────┘      └────────┬───────┘
        │                       │
        └───────────┬───────────┘
                    │
                    ▼
            ┌───────────────────────┐
            │  Call LLM API         │
            │  • Send Prompt        │
            │  • Receive Response   │
            └───────┬───────────────┘
                    │
                    ▼
            ┌───────────────────────┐
            │  Parse Response       │
            │  • Extract Query      │
            │  • Validate Syntax    │
            │  • Clean Formatting   │
            └───────┬───────────────┘
                    │
                    ▼
            ┌───────────────────────┐
            │  Return Generated     │
            │  Query                │
            └───────────────────────┘
```

**Example LLM Interactions:**

**SQL Query Generation:**
```
Input: "Show me all customers who made purchases in the last 30 days"
Schema: customers(id, name, email), orders(id, customer_id, order_date, total_amount)

LLM Output:
SELECT DISTINCT c.id, c.name, c.email
FROM customers c
INNER JOIN orders o ON c.id = o.customer_id
WHERE o.order_date >= NOW() - INTERVAL '30 days'
ORDER BY c.name;
```

**MongoDB Query Generation:**
```
Input: "Find all users with premium subscription"
Schema: users{_id, name, email, subscription{type, status}}

LLM Output:
db.users.find({
  "subscription.type": "premium",
  "subscription.status": "active"
})
```

**Cypher Query Generation:**
```
Input: "Find all friends of John who work at the same company"
Schema: Person-[:FRIENDS_WITH]->Person, Person-[:WORKS_AT]->Company

LLM Output:
MATCH (john:Person {name: 'John'})-[:FRIENDS_WITH]->(friend:Person)
MATCH (john)-[:WORKS_AT]->(company:Company)<-[:WORKS_AT]-(friend)
RETURN friend.name, company.name
```


### Step 5: Query Execution (Optional)

**Execution Flow:**
```
┌─────────────────────────────────────────────────────────────┐
│  Query Executor                                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
            ┌───────────────────────┐
            │  Check Execute Flag   │
            └───────┬───────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐      ┌────────────────┐
│ execute=false │      │ execute=true   │
│ Return Query  │      │ Continue       │
└───────────────┘      └────────┬───────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │  Validate Query       │
                    │  • Syntax Check       │
                    │  • Safety Check       │
                    │  • No DROP/DELETE     │
                    └───────┬───────────────┘
                            │
                            ▼
                    ┌───────────────────────┐
                    │  Get Connector        │
                    │  • SQL Connector      │
                    │  • NoSQL Connector    │
                    │  • Graph Connector    │
                    │  • GraphQL Connector  │
                    └───────┬───────────────┘
                            │
                            ▼
                    ┌───────────────────────┐
                    │  Connect to Database  │
                    │  • Use Credentials    │
                    │  • Connection Pool    │
                    └───────┬───────────────┘
                            │
                            ▼
                    ┌───────────────────────┐
                    │  Execute Query        │
                    │  • Run Query          │
                    │  • Measure Time       │
                    │  • Handle Errors      │
                    └───────┬───────────────┘
                            │
                            ▼
                    ┌───────────────────────┐
                    │  Fetch Results        │
                    │  • Get All Rows       │
                    │  • Apply Limits       │
                    └───────┬───────────────┘
                            │
                            ▼
                    ┌───────────────────────┐
                    │  Format Results       │
                    │  • Convert to JSON    │
                    │  • Handle Types       │
                    │  • Add Metadata       │
                    └───────┬───────────────┘
                            │
                            ▼
                    ┌───────────────────────┐
                    │  Return Response      │
                    └───────────────────────┘
```

### Step 6: Response Formation

**Response Structure:**
```json
{
  "query": "SELECT * FROM customers WHERE ...",
  "executed": true,
  "results": [
    {"id": 1, "name": "John Doe", "email": "john@example.com"},
    {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
  ],
  "metadata": {
    "row_count": 2,
    "execution_time_ms": 45,
    "database_type": "postgresql"
  }
}
```

## Query Type Routing

### SQL Query Routing

```
nl_to_sql Tool
      │
      ▼
┌─────────────────────────────────────────┐
│  SQL Handler                            │
│  • Parse database_type parameter        │
│  • Validate connection config           │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  SQLConnector Factory                   │
│  • Create appropriate connector         │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┼─────────┬─────────┬────────┐
    │         │         │         │        │
    ▼         ▼         ▼         ▼        ▼
┌────────┐ ┌──────┐ ┌───────┐ ┌──────┐ ┌──────────┐
│ MySQL  │ │ PG   │ │Oracle │ │MSSQL │ │Snowflake │
└────┬───┘ └───┬──┘ └───┬───┘ └───┬──┘ └────┬─────┘
     │         │        │         │         │
     └─────────┴────────┴─────────┴─────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │  Execute SQL Query  │
              └─────────────────────┘
```

**Database-Specific Connection:**
```python
# MySQL
connection = pymysql.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE
)

# PostgreSQL
connection = psycopg2.connect(
    host=POSTGRESQL_HOST,
    user=POSTGRESQL_USER,
    password=POSTGRESQL_PASSWORD,
    database=POSTGRESQL_DATABASE
)

# Snowflake
connection = snowflake.connector.connect(
    account=SNOWFLAKE_ACCOUNT,
    user=SNOWFLAKE_USER,
    password=SNOWFLAKE_PASSWORD,
    database=SNOWFLAKE_DATABASE,
    warehouse=SNOWFLAKE_WAREHOUSE
)
```

### NoSQL Query Routing

```
nl_to_nosql Tool
      │
      ▼
┌─────────────────────────────────────────┐
│  NoSQL Handler                          │
│  • Parse database_type parameter        │
│  • Validate connection config           │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  NoSQLConnector Factory                 │
│  • Create appropriate connector         │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
    ▼         ▼         ▼         ▼
┌─────────┐ ┌───────┐ ┌──────────┐ ┌──────────┐
│MongoDB  │ │Redis  │ │Cassandra │ │DynamoDB  │
└────┬────┘ └───┬───┘ └────┬─────┘ └────┬─────┘
     │          │          │            │
     └──────────┴──────────┴────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │  Execute NoSQL Query│
              └─────────────────────┘
```

**Database-Specific Operations:**
```python
# MongoDB
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]
results = db.collection.find(query)

# Redis
client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD
)
result = client.execute_command(query)

# DynamoDB
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(table_name)
response = table.query(KeyConditionExpression=query)
```

### Graph Query Routing

```
nl_to_cypher Tool
      │
      ▼
┌─────────────────────────────────────────┐
│  Graph Handler                          │
│  • Parse database_type parameter        │
│  • Validate connection config           │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  GraphConnector Factory                 │
│  • Create appropriate connector         │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┼─────────┬─────────┐
    │         │         │         │
    ▼         ▼         ▼         ▼
┌───────┐ ┌─────────┐ ┌────────┐ ┌─────────┐
│Neo4j  │ │ArangoDB │ │Neptune │ │CosmosDB │
└───┬───┘ └────┬────┘ └───┬────┘ └────┬────┘
    │          │          │           │
    └──────────┴──────────┴───────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │  Execute Graph Query│
              └─────────────────────┘
```

**Database-Specific Operations:**
```python
# Neo4j (Cypher)
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
with driver.session() as session:
    result = session.run(cypher_query)

# ArangoDB (AQL)
client = ArangoClient(hosts=ARANGO_HOST)
db = client.db(ARANGO_DATABASE, username=ARANGO_USER, password=ARANGO_PASSWORD)
cursor = db.aql.execute(aql_query)

# Neptune (Gremlin)
client = Client(f"wss://{NEPTUNE_ENDPOINT}:8182/gremlin", 'g')
results = client.submit(gremlin_query).all().result()
```

### GraphQL Query Routing

```
nl_to_graphql Tool
      │
      ▼
┌─────────────────────────────────────────┐
│  GraphQL Handler                        │
│  • Parse api_endpoint parameter         │
│  • Validate API token                   │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  GraphQLConnector                       │
│  • Setup HTTP client                    │
│  • Add authentication headers           │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┼─────────┐
    │         │         │
    ▼         ▼         ▼
┌─────────┐ ┌───────┐ ┌────────┐
│Generic  │ │Saleor │ │Custom  │
│GraphQL  │ │API    │ │API     │
└────┬────┘ └───┬───┘ └───┬────┘
     │          │         │
     └──────────┴─────────┘
                │
                ▼
      ┌─────────────────────┐
      │  Execute GraphQL    │
      │  Query via HTTP     │
      └─────────────────────┘
```

**GraphQL Execution:**
```python
# Generic GraphQL
headers = {"Authorization": f"Bearer {GRAPHQL_API_TOKEN}"}
response = httpx.post(
    endpoint,
    json={"query": graphql_query},
    headers=headers
)

# Saleor API
headers = {"Authorization": f"Bearer {SALEOR_API_TOKEN}"}
response = httpx.post(
    SALEOR_API_ENDPOINT,
    json={"query": graphql_query},
    headers=headers
)
```


## Database-Specific Workflows

### SQL Workflow (PostgreSQL Example)

```
User Query: "Show me all customers who made purchases in the last 30 days"
Database: PostgreSQL

Step 1: Request Reception
┌─────────────────────────────────────────┐
│ MCP Client sends:                       │
│ {                                       │
│   "tool": "nl_to_sql",                  │
│   "arguments": {                        │
│     "query": "Show me all customers...",│
│     "database_type": "postgresql",      │
│     "execute": true                     │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
                    ↓
Step 2: Schema Retrieval
┌─────────────────────────────────────────┐
│ Check Cache: postgresql_localhost_mydb  │
│ Cache Miss → Connect to PostgreSQL      │
│                                         │
│ SELECT table_name, column_name,         │
│        data_type                        │
│ FROM information_schema.columns         │
│ WHERE table_schema = 'public'           │
│                                         │
│ Result:                                 │
│ • customers (id, name, email)           │
│ • orders (id, customer_id, order_date)  │
│                                         │
│ Cache schema for 24 hours               │
└─────────────────────────────────────────┘
                    ↓
Step 3: Query Generation
┌─────────────────────────────────────────┐
│ LLM Prompt:                             │
│ "Generate PostgreSQL query for:         │
│  Show me all customers who made         │
│  purchases in the last 30 days          │
│                                         │
│  Schema: customers, orders              │
│  Use proper JOIN and date functions"    │
│                                         │
│ LLM Response:                           │
│ SELECT DISTINCT c.id, c.name, c.email   │
│ FROM customers c                        │
│ INNER JOIN orders o                     │
│   ON c.id = o.customer_id               │
│ WHERE o.order_date >=                   │
│   NOW() - INTERVAL '30 days'            │
│ ORDER BY c.name;                        │
└─────────────────────────────────────────┘
                    ↓
Step 4: Query Execution
┌─────────────────────────────────────────┐
│ Connect to PostgreSQL                   │
│ Execute query                           │
│ Fetch results                           │
│                                         │
│ Results:                                │
│ [                                       │
│   {id: 1, name: "John", email: "..."},  │
│   {id: 5, name: "Jane", email: "..."}   │
│ ]                                       │
│                                         │
│ Execution time: 45ms                    │
│ Row count: 2                            │
└─────────────────────────────────────────┘
                    ↓
Step 5: Response
┌─────────────────────────────────────────┐
│ Return to MCP Client:                   │
│ {                                       │
│   "query": "SELECT DISTINCT...",        │
│   "executed": true,                     │
│   "results": [...],                     │
│   "metadata": {                         │
│     "row_count": 2,                     │
│     "execution_time_ms": 45             │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
```

### NoSQL Workflow (MongoDB Example)

```
User Query: "Find all users with premium subscription"
Database: MongoDB

Step 1: Request Reception
┌─────────────────────────────────────────┐
│ MCP Client sends:                       │
│ {                                       │
│   "tool": "nl_to_nosql",                │
│   "arguments": {                        │
│     "query": "Find all users with...",  │
│     "database_type": "mongodb",         │
│     "execute": true                     │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
                    ↓
Step 2: Schema Sampling
┌─────────────────────────────────────────┐
│ Check Cache: mongodb_localhost_mydb     │
│ Cache Miss → Connect to MongoDB         │
│                                         │
│ Sample documents from collections:      │
│ db.users.findOne()                      │
│                                         │
│ Sample Result:                          │
│ {                                       │
│   "_id": ObjectId("..."),               │
│   "name": "John Doe",                   │
│   "email": "john@example.com",          │
│   "subscription": {                     │
│     "type": "premium",                  │
│     "status": "active",                 │
│     "expires_at": ISODate("...")        │
│   }                                     │
│ }                                       │
│                                         │
│ Cache schema for 24 hours               │
└─────────────────────────────────────────┘
                    ↓
Step 3: Query Generation
┌─────────────────────────────────────────┐
│ LLM Prompt:                             │
│ "Generate MongoDB query for:            │
│  Find all users with premium            │
│  subscription                           │
│                                         │
│  Schema: users collection with          │
│  nested subscription object"            │
│                                         │
│ LLM Response:                           │
│ db.users.find({                         │
│   "subscription.type": "premium",       │
│   "subscription.status": "active"       │
│ })                                      │
└─────────────────────────────────────────┘
                    ↓
Step 4: Query Execution
┌─────────────────────────────────────────┐
│ Connect to MongoDB                      │
│ Execute query                           │
│ Fetch documents                         │
│                                         │
│ Results:                                │
│ [                                       │
│   {_id: "...", name: "John", ...},      │
│   {_id: "...", name: "Jane", ...}       │
│ ]                                       │
│                                         │
│ Document count: 2                       │
└─────────────────────────────────────────┘
                    ↓
Step 5: Response
┌─────────────────────────────────────────┐
│ Return to MCP Client:                   │
│ {                                       │
│   "query": "db.users.find({...})",      │
│   "executed": true,                     │
│   "results": [...],                     │
│   "metadata": {                         │
│     "document_count": 2                 │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
```

### Graph Workflow (Neo4j Example)

```
User Query: "Find all friends of John who work at the same company"
Database: Neo4j

Step 1: Request Reception
┌─────────────────────────────────────────┐
│ MCP Client sends:                       │
│ {                                       │
│   "tool": "nl_to_cypher",               │
│   "arguments": {                        │
│     "query": "Find all friends of...",  │
│     "database_type": "neo4j",           │
│     "execute": true                     │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
                    ↓
Step 2: Schema Introspection
┌─────────────────────────────────────────┐
│ Check Cache: neo4j_localhost_neo4j      │
│ Cache Miss → Connect to Neo4j           │
│                                         │
│ CALL db.labels()                        │
│ CALL db.relationshipTypes()             │
│ CALL db.schema.nodeTypeProperties()     │
│                                         │
│ Result:                                 │
│ Node Labels: Person, Company            │
│ Relationships: FRIENDS_WITH, WORKS_AT   │
│ Properties:                             │
│   Person: name, email, age              │
│   Company: name, industry               │
│                                         │
│ Cache schema for 24 hours               │
└─────────────────────────────────────────┘
                    ↓
Step 3: Query Generation
┌─────────────────────────────────────────┐
│ LLM Prompt:                             │
│ "Generate Cypher query for:             │
│  Find all friends of John who work      │
│  at the same company                    │
│                                         │
│  Schema: Person-[:FRIENDS_WITH]->Person │
│          Person-[:WORKS_AT]->Company"   │
│                                         │
│ LLM Response:                           │
│ MATCH (john:Person {name: 'John'})      │
│   -[:FRIENDS_WITH]->(friend:Person)     │
│ MATCH (john)-[:WORKS_AT]->(company)     │
│   <-[:WORKS_AT]-(friend)                │
│ RETURN friend.name, company.name        │
└─────────────────────────────────────────┘
                    ↓
Step 4: Query Execution
┌─────────────────────────────────────────┐
│ Connect to Neo4j                        │
│ Execute Cypher query                    │
│ Fetch results                           │
│                                         │
│ Results:                                │
│ [                                       │
│   {friend: "Alice", company: "Acme"},   │
│   {friend: "Bob", company: "Acme"}      │
│ ]                                       │
│                                         │
│ Node count: 2                           │
└─────────────────────────────────────────┘
                    ↓
Step 5: Response
┌─────────────────────────────────────────┐
│ Return to MCP Client:                   │
│ {                                       │
│   "query": "MATCH (john:Person...",     │
│   "executed": true,                     │
│   "results": [...],                     │
│   "metadata": {                         │
│     "node_count": 2                     │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
```

### GraphQL Workflow Example

```
User Query: "Get all products with their categories and prices"
API: Generic GraphQL Endpoint

Step 1: Request Reception
┌─────────────────────────────────────────┐
│ MCP Client sends:                       │
│ {                                       │
│   "tool": "nl_to_graphql",              │
│   "arguments": {                        │
│     "query": "Get all products...",     │
│     "api_endpoint": "https://...",      │
│     "execute": true                     │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
                    ↓
Step 2: Schema Introspection
┌─────────────────────────────────────────┐
│ Check Cache: graphql_api.example.com    │
│ Cache Miss → Query GraphQL Schema       │
│                                         │
│ Introspection Query:                    │
│ { __schema {                            │
│     types { name, fields { name } }     │
│   }                                     │
│ }                                       │
│                                         │
│ Result:                                 │
│ Types: Product, Category                │
│ Product fields: id, name, price,        │
│                 category                │
│ Category fields: id, name               │
│                                         │
│ Cache schema for 24 hours               │
└─────────────────────────────────────────┘
                    ↓
Step 3: Query Generation
┌─────────────────────────────────────────┐
│ LLM Prompt:                             │
│ "Generate GraphQL query for:            │
│  Get all products with their            │
│  categories and prices                  │
│                                         │
│  Schema: Product, Category types"       │
│                                         │
│ LLM Response:                           │
│ query {                                 │
│   products {                            │
│     id                                  │
│     name                                │
│     price                               │
│     category {                          │
│       id                                │
│       name                              │
│     }                                   │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
                    ↓
Step 4: Query Execution
┌─────────────────────────────────────────┐
│ HTTP POST to GraphQL endpoint           │
│ Headers: Authorization Bearer token     │
│ Body: {"query": "query { ... }"}        │
│                                         │
│ Response:                               │
│ {                                       │
│   "data": {                             │
│     "products": [                       │
│       {                                 │
│         "id": "1",                      │
│         "name": "Widget",               │
│         "price": 29.99,                 │
│         "category": {                   │
│           "id": "10",                   │
│           "name": "Electronics"         │
│         }                               │
│       }                                 │
│     ]                                   │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
                    ↓
Step 5: Response
┌─────────────────────────────────────────┐
│ Return to MCP Client:                   │
│ {                                       │
│   "query": "query { products { ... }}", │
│   "executed": true,                     │
│   "results": {...},                     │
│   "metadata": {                         │
│     "status_code": 200                  │
│   }                                     │
│ }                                       │
└─────────────────────────────────────────┘
```


## Schema Caching Mechanism

### Cache Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Schema Cache Lifecycle                   │
└─────────────────────────────────────────────────────────────┘

Initial Request (Cache Miss)
────────────────────────────
Request → Check Cache → Not Found → Fetch Schema → Cache → Return
                                         ↓
                                    [Database]
                                         ↓
                                    Introspect
                                         ↓
                                    Store in Cache
                                    (TTL: 24 hours)

Subsequent Requests (Cache Hit)
───────────────────────────────
Request → Check Cache → Found & Valid → Return Cached Schema
                            ↓
                       [No DB Call]
                            ↓
                    Faster Response

Cache Expiration
────────────────
Request → Check Cache → Found but Expired → Fetch Fresh → Update Cache
                                                  ↓
                                             [Database]

Manual Refresh
──────────────
refresh_schema_cache Tool → Invalidate Cache → Fetch Fresh → Update Cache
                                                    ↓
                                               [Database]
```

### Cache Key Generation

```python
def generate_cache_key(database_type: str, host: str, database: str) -> str:
    """
    Generate unique cache key for database schema
    
    Examples:
    - postgresql_localhost_mydb
    - mongodb_cluster.example.com_production
    - neo4j_bolt://localhost:7687_neo4j
    """
    # Sanitize components
    safe_host = host.replace(':', '_').replace('/', '_')
    safe_db = database.replace('/', '_')
    
    return f"{database_type}_{safe_host}_{safe_db}"
```

### Cache Storage Structure

```
cache/
├── postgresql_localhost_mydb.json
│   {
│     "timestamp": 1701234567,
│     "ttl": 86400,
│     "schema": {
│       "tables": [...]
│     }
│   }
│
├── mongodb_localhost_users.json
│   {
│     "timestamp": 1701234890,
│     "ttl": 86400,
│     "schema": {
│       "collections": [...]
│     }
│   }
│
└── neo4j_localhost_neo4j.json
    {
      "timestamp": 1701235123,
      "ttl": 86400,
      "schema": {
        "node_labels": [...],
        "relationships": [...]
      }
    }
```

### Cache Validation

```python
def is_cache_valid(cache_entry: dict) -> bool:
    """
    Check if cached schema is still valid
    """
    current_time = time.time()
    cache_time = cache_entry.get('timestamp', 0)
    ttl = cache_entry.get('ttl', 86400)  # 24 hours default
    
    age = current_time - cache_time
    
    return age < ttl
```

## Error Handling Flow

### Error Types and Handling

```
┌─────────────────────────────────────────────────────────────┐
│                    Error Handling Flow                      │
└─────────────────────────────────────────────────────────────┘

Connection Errors
─────────────────
Database Unreachable → Retry (3 attempts) → Fail
                            ↓
                    Return Error Response:
                    {
                      "error": "Connection failed",
                      "details": "Could not connect to...",
                      "suggestion": "Check credentials and network"
                    }

Schema Introspection Errors
───────────────────────────
Permission Denied → Return Error
                        ↓
                    {
                      "error": "Schema access denied",
                      "details": "User lacks permissions",
                      "suggestion": "Grant schema read permissions"
                    }

LLM API Errors
──────────────
Rate Limit → Wait & Retry → Success/Fail
API Error → Return Error
                ↓
            {
              "error": "LLM API error",
              "details": "Rate limit exceeded",
              "suggestion": "Wait and retry"
            }

Query Execution Errors
──────────────────────
Syntax Error → Return Error with Query
                    ↓
                {
                  "error": "Query execution failed",
                  "query": "SELECT * FROM...",
                  "details": "Syntax error near...",
                  "suggestion": "Review generated query"
                }

Validation Errors
─────────────────
Dangerous Operation → Block Execution
                          ↓
                      {
                        "error": "Unsafe operation",
                        "details": "DROP/DELETE detected",
                        "suggestion": "Use read-only operations"
                      }
```

### Error Recovery Strategies

```python
# Connection Retry Logic
def connect_with_retry(connector, max_retries=3):
    for attempt in range(max_retries):
        try:
            return connector.connect()
        except ConnectionError as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff

# Fallback to Cached Schema
def get_schema_with_fallback(cache_key, connector):
    try:
        # Try to fetch fresh schema
        schema = connector.get_schema()
        cache.set(cache_key, schema)
        return schema
    except Exception as e:
        # Fall back to expired cache if available
        cached = cache.get(cache_key, ignore_ttl=True)
        if cached:
            logger.warning(f"Using expired cache due to error: {e}")
            return cached
        raise

# Graceful Degradation
def execute_query_safe(query, connector):
    try:
        return connector.execute(query)
    except Exception as e:
        # Return query without execution
        return {
            "query": query,
            "executed": False,
            "error": str(e),
            "suggestion": "Review query and try manual execution"
        }
```

## Example Workflows

### Example 1: Complete SQL Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ User: "Show me top 10 customers by revenue this year"       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ MCP Client → Server                                         │
│ Tool: nl_to_sql                                             │
│ Database: postgresql                                        │
│ Execute: true                                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Schema Cache Check                                          │
│ Key: postgresql_localhost_sales_db                          │
│ Status: HIT (cached 2 hours ago)                            │
│ Schema: customers, orders, order_items tables               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LLM Query Generation (OpenAI GPT-4)                         │
│                                                             │
│ Generated Query:                                            │
│ SELECT                                                      │
│   c.id,                                                     │
│   c.name,                                                   │
│   SUM(oi.quantity * oi.unit_price) as total_revenue         │ 
│ FROM customers c                                            │
│ JOIN orders o ON c.id = o.customer_id                       │
│ JOIN order_items oi ON o.id = oi.order_id                   │
│ WHERE EXTRACT(YEAR FROM o.order_date) =                     │
│       EXTRACT(YEAR FROM CURRENT_DATE)                       │
│ GROUP BY c.id, c.name                                       │
│ ORDER BY total_revenue DESC                                 │
│ LIMIT 10;                                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Query Execution                                             │
│ Connection: PostgreSQL via psycopg2                         │
│ Execution Time: 127ms                                       │
│ Rows Returned: 10                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Response to Client                                          │
│ {                                                           │
│   "query": "SELECT c.id, c.name...",                        │
│   "executed": true,                                         │
│   "results": [                                              │
│     {"id": 42, "name": "Acme Corp", "revenue": 125000},     │
│     {"id": 17, "name": "TechStart", "revenue": 98000},      │
│     ...                                                     │
│   ],                                                        │
│   "metadata": {                                             │
│     "row_count": 10,                                        │
│     "execution_time_ms": 127,                               │
│     "database_type": "postgresql"                           │
│   }                                                         │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
```

### Example 2: MongoDB Aggregation Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ User: "Count orders by status for each customer"            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ MCP Client → Server                                         │
│ Tool: nl_to_nosql                                           │
│ Database: mongodb                                           │
│ Execute: true                                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Schema Cache Check                                          │
│ Key: mongodb_localhost_ecommerce                            │
│ Status: MISS (first request)                                │
│ Action: Sample documents from collections                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Schema Introspection                                        │
│ db.orders.findOne() →                                       │
│ {                                                           │
│   "_id": ObjectId("..."),                                   │
│   "customer_id": "cust_123",                                │
│   "status": "completed",                                    │
│   "items": [...],                                           │
│   "total": 99.99                                            │
│ }                                                           │
│ Cache for 24 hours                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ LLM Query Generation (Anthropic Claude)                     │
│                                                             │
│ Generated Query:                                            │
│ db.orders.aggregate([                                       │
│   {                                                         │
│     $group: {                                               │
│       _id: {                                                │
│         customer_id: "$customer_id",                        │
│         status: "$status"                                   │
│       },                                                    │
│       count: { $sum: 1 }                                    │
│     }                                                       │
│   },                                                        │
│   {                                                         │
│     $sort: { "_id.customer_id": 1, "_id.status": 1 }        │ 
│   }                                                         │
│ ])                                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Query Execution                                             │
│ Connection: MongoDB via pymongo                             │
│ Execution Time: 89ms                                        │
│ Documents Returned: 25                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Response to Client                                          │
│ {                                                           │
│   "query": "db.orders.aggregate([...])",                    │
│   "executed": true,                                         │
│   "results": [                                              │
│     {"customer_id": "cust_123", "status": "completed",      │
│      "count": 5},                                           │
│     {"customer_id": "cust_123", "status": "pending",        │
│      "count": 2},                                           │
│     ...                                                     │
│   ],                                                        │
│   "metadata": {                                             │
│     "document_count": 25,                                   │
│     "database_type": "mongodb"                              │
│   }                                                         │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
```

## Performance Considerations

### Optimization Points

1. **Schema Caching**
   - Reduces database load by 90%
   - Eliminates repeated introspection queries
   - 24-hour TTL balances freshness and performance

2. **Connection Pooling**
   - Reuse database connections
   - Reduce connection overhead
   - Handle concurrent requests efficiently

3. **Query Optimization**
   - LLM generates indexed queries
   - Use LIMIT clauses for large result sets
   - Leverage database-specific optimizations

4. **Async Operations**
   - Non-blocking I/O for database calls
   - Concurrent request handling
   - Better resource utilization

### Typical Response Times

```
Operation                          Time (Cached)    Time (Uncached)
─────────────────────────────────────────────────────────────────
Schema Retrieval                   < 1ms            200-500ms
LLM Query Generation               1-3s             1-3s
Query Execution (Simple)           10-100ms         10-100ms
Query Execution (Complex)          100-500ms        100-500ms
Total (Simple Query, Cached)       1-3s             2-4s
Total (Complex Query, Cached)      1.5-3.5s         2.5-5s
```

## Conclusion

The MCP Natural Language to Data Endpoints workflow is designed for:

- **Modularity**: Each component is independent and replaceable
- **Performance**: Schema caching and connection pooling optimize speed
- **Flexibility**: Support for 20+ database types with unified interface
- **Reliability**: Comprehensive error handling and recovery
- **Scalability**: Async operations and stateless design

The workflow ensures that natural language queries are efficiently transformed into optimized database-specific queries while maintaining high performance and reliability across diverse database systems.
