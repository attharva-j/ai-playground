# Azure MCP ES-GDB Chat — Technical Documentation

## Business Use Case

Enterprise knowledge workers routinely need to answer questions like:
- "How many executive search assignments did we run in the financial services sector last quarter?"
- "Generate a full company profile for [Company Name] including leadership, financials, and recent news."
- "Who are the lead consultants on open assignments at [Company Name]?"

Answering these questions traditionally requires logging into multiple systems — a graph database for relationship and assignment data, an Elasticsearch cluster for company and person profiles, and a Databricks warehouse for structured analytics — and manually stitching results together. This is slow, error-prone, and inaccessible to non-technical users.

This project solves that by deploying an **MCP (Model Context Protocol) server** as an **Azure Web App**, connected to a **Developer Mode-enabled custom chat interface**. Users ask questions in plain English. The server classifies intent, routes to the right data source, generates the appropriate query (Cypher, Elasticsearch DSL, or SQL), executes it, and returns an AI-summarized answer — or a fully formatted PDF SmartPack — in seconds.

### Value It Brings

- Single natural-language interface over three heterogeneous data systems
- Eliminates manual cross-system lookups for relationship intelligence and executive briefings
- Standardizes SmartPack (company/person dossier) generation and PDF delivery
- Secure, auditable, prompt-injection-resistant access to sensitive enterprise data
- Accessible to non-technical users through a familiar chat interface

### Problem It Solves & How

The core problem is **data fragmentation + access friction**. The solution is a layered architecture:

1. An LLM classifies the user's intent (QnA lookup vs. SmartPack generation vs. other)
2. A routing layer selects the right connector (Neo4j, Elasticsearch, Databricks)
3. The LLM generates a connector-specific query using live schema context
4. The connector executes the query and returns raw results
5. The LLM post-processes results into a coherent, human-readable response
6. For SmartPacks, a PDF is generated and uploaded to Azure Blob Storage with a download link

---

## Index

1. [System Architecture](#1-system-architecture)
2. [Component Reference](#2-component-reference)
3. [End-to-End Query Workflow](#3-end-to-end-query-workflow)
4. [Intent Classification](#4-intent-classification)
5. [Connector Routing](#5-connector-routing)
6. [GraphDB (Neo4j) QnA Flow](#6-graphdb-neo4j-qna-flow)
7. [SmartPack Generation Flow](#7-smartpack-generation-flow)
8. [PDF Generation & Storage](#8-pdf-generation--storage)
9. [Security & Guardrails](#9-security--guardrails)
10. [REST API Reference](#10-rest-api-reference)
11. [MCP Tools Reference](#11-mcp-tools-reference)
12. [Configuration Reference](#12-configuration-reference)
13. [Prompting Guide](#13-prompting-guide)

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Custom Chat Interface                        │
│              (Developer Mode, MCP-compatible client)            │
└────────────────────────┬────────────────────────────────────────┘
                         │  MCP Protocol (SSE or Streamable HTTP)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Azure Web App                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Starlette ASGI App (server.py)                          │   │
│  │  ├── /mcp  → FastMCP SSE endpoint                        │   │
│  │  ├── /sse  → FastMCP Streamable HTTP endpoint            │   │
│  │  └── /     → Flask REST API (WSGIMiddleware)             │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  mcp_app.py — MCP Tools + Flask Routes                   │   │
│  │  ├── Intent Classifier (OpenAI)                          │   │
│  │  ├── Connector Router                                    │   │
│  │  ├── Query Generator (OpenAI + schema context)           │   │
│  │  ├── Connector Executor                                  │   │
│  │  └── Post-Processor (OpenAI summarization)               │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
  Neo4j GraphDB    Elasticsearch       Databricks
  (Bolt driver)    (HTTP REST)         (REST API)
       │
       └── NTLM REST API (optional enrichment overlay)

                    Azure Key Vault (secrets)
                    Azure Blob Storage (PDF SmartPacks)
```

---

## 2. Component Reference

### `server.py` — ASGI Entry Point

Mounts the MCP server and Flask app into a single Starlette ASGI application. Handles both SSE and Streamable HTTP MCP transports. Startup is managed by Gunicorn with Uvicorn workers.

### `mcp_app.py` — Core Application Logic

Creates the FastMCP server instance and Flask app. Defines all MCP tools (`search`, `qna`, `smartpack`, `fetch`) and Flask REST routes. Orchestrates the full pipeline: intent classification → connector routing → query generation → execution → post-processing.

### `utils.py` — Utilities & Connector Helpers

~1700 lines of shared utilities including:
- Connector factory functions (`_es()`, `_gdb()`, `_dbx()`, `_ntlm()`)
- Secrets loading from env or Azure Key Vault (`_get_secrets()`)
- OpenAI call wrappers (`_openai_json_call()`, `_classify_intent()`)
- Graph schema discovery and caching (`_graph_schema_context()`)
- Cypher query safety rewrites (`rewrite_string_equals_to_smart()`)
- Elasticsearch query builder (`build_elasticsearch_query()`)
- Azure Storage upload/download (`upload_pdf_to_storage()`, `download_pdf_from_storage()`)

### `DataSourceConnectors/` — Data Source Adapters

| File | Connector | Protocol |
|---|---|---|
| `graphdb_connector.py` | Neo4j | Bolt (neo4j driver) |
| `elasticsearch_connector.py` | Elasticsearch | HTTP REST |
| `databricks_connector.py` | Databricks | REST API (SQL + DBFS) |
| `ntlm_rest_connector.py` | Internal REST APIs | NTLM HTTP |

### `Mapping/` — SmartPack Data Transformation

- `smartpack_entities.py`: `CompanySmartpack` and `PersonSmartpack` classes that fetch ES data, merge NTLM overlays, build structured JSON summaries, and trigger PDF generation
- `config_mapper.py`: `ConfigMapper` class that applies JSON-defined path mappings to transform summary data into PDF content structures
- `mapping_configs/company_mapping.json`: Field path mappings for company PDFs
- `mapping_configs/person_mapping.json`: Field path mappings for person PDFs

### `smartpackPdfMapping/smartpack_generator.py` — PDF Generation

ReportLab-based PDF generator. Exposes `generate_pdf_company()` and `generate_pdf_person()`. Handles multi-section layouts including key info tables, leadership tables, news sections, assignment history, and sustainability sections.

### `prompt_injection_detector.py` — Security Guardrail

Heuristic regex-based detector for prompt injection attempts. Checks for instruction override patterns, jailbreak keywords, role impersonation, system token injection, and requests for secrets or external execution.

### `prop_resolver.py` — Graph Property Resolver

Fuzzy property name resolver backed by a live Neo4j schema cache. Resolves user-facing property names (e.g., "full name") to canonical graph property names (e.g., `FullName`) using normalized string matching and difflib.

### `degree_resolver.py` — Degree Fuzzy Matcher

Resolves free-text degree/field-of-study phrases to canonical values from a curated list using token overlap and sequence similarity scoring.

---

## 3. End-to-End Query Workflow

This is the complete lifecycle of a user query from the chat interface to the response.

```
User types query in chat
        │
        ▼
[1] Prompt Injection Check
    prompt_injection_detector.is_prompt_injection(query)
    → If detected: return error, do not proceed
        │
        ▼
[2] Intent Classification
    OpenAI call with classify_intent system prompt
    → Returns: { intent, baseQuery, instance, rationale }
    → intent ∈ { qna, smartpack, other }
        │
        ├── intent == "smartpack"
        │       ▼
        │   [3a] SmartPack Flow (see §7)
        │
        ├── intent == "qna"
        │       ▼
        │   [3b] QnA Flow (see §6)
        │
        └── intent == "other"
                ▼
            [3c] Fallback / general response
```

---

## 4. Intent Classification

The intent classifier is an OpenAI call using the `classify_intent` prompt from `config/mcp_config.json`.

**Output schema:**

```json
{
  "intent": "qna | smartpack | other",
  "rationale": "short explanation",
  "baseQuery": "companySmartpack | personSmartpack | other",
  "instance": "extracted entity name or empty string"
}
```

**Decision rules:**

| Intent | When to use |
|---|---|
| `qna` | Factual lookups, lists, counts, comparisons, searches about entities or relationships. Queries mentioning companies, people, industries, locations, projects, or assignments. |
| `smartpack` | Explicit requests to generate/compile/create a profile, dossier, brief, or SmartPack for a named entity. |
| `other` | Purely conversational, procedural, or unrelated queries. |

---

## 5. Connector Routing

After intent classification, the routing layer selects which data connector(s) to use:

| Intent | Primary Connector | Fallback |
|---|---|---|
| `qna` | Neo4j GraphDB | Elasticsearch |
| `smartpack` | Elasticsearch | Databricks (if configured) |
| `other` | Elasticsearch | — |

The `SMARTPACK_BACKENDS` and `SMARTPACK_PRIMARY` environment variables control which backends are active for SmartPack queries.

---

## 6. GraphDB (Neo4j) QnA Flow

```
User query (intent=qna)
        │
        ▼
[1] Schema Discovery
    _graph_schema_context() — cached for GRAPH_SCHEMA_TTL_SECONDS (default 15 min)
    Introspects Neo4j: node labels, relationship types, property names
        │
        ▼
[2] Alias Augmentation
    _find_entity_aliases_in_graph() — looks up canonical names for tokens
    e.g., "Stanford" → "Stanford University" (from graph data)
    _augment_query_with_aliases() — appends "(aka ...)" hints to query
        │
        ▼
[3] Cypher Generation
    _generate_graphdb_request_with_schema()
    OpenAI call with:
    - Full schema context (labels, relationships, properties)
    - Domain rules (project queries, experience queries, education queries)
    - Degree resolver results (if education-related)
    - Property resolver for fuzzy property name matching
    → Returns: { cypher: "MATCH ... RETURN ..." }
        │
        ▼
[4] Cypher Safety Rewrite
    rewrite_string_equals_to_smart()
    Converts brittle exact-match predicates to tolerant STARTS WITH / CONTAINS
    e.g., n.CompanyName = 'Harvard' → toLower(n.CompanyName) STARTS WITH 'harvard'
        │
        ▼
[5] Query Execution
    GraphDBConnector.query_cypher()
    Returns list of row dicts
        │
        ▼
[6] Result Coercion
    _coerce_graph_rows() — converts Neo4j types (Node, Relationship, Path) to JSON-serializable dicts
        │
        ▼
[7] Post-Processing
    _post_process_with_openai()
    OpenAI call to summarize raw graph results into a human-readable response
        │
        ▼
Response returned to chat interface
```

---

## 7. SmartPack Generation Flow

SmartPacks are structured PDF dossiers for a company or person. The flow differs slightly between the two.

```
User query (intent=smartpack, instance="[Entity Name]")
        │
        ▼
[1] Determine entity type
    baseQuery == "companySmartpack" → CompanySmartpack
    baseQuery == "personSmartpack"  → PersonSmartpack
        │
        ▼
[2] Build Elasticsearch Query
    CompanySmartpack.get_smartpack_config() or PersonSmartpack.get_smartpack_config()
    Uses intents.json for index names, source fields, and search field
    Constructs match_phrase query against CompanyName or Overview.FullName
        │
        ▼
[3] Execute Elasticsearch Query
    ElasticSearchConnector.search()
    Returns top-N hits with configured source fields
        │
        ▼
[4] NTLM Overlay (optional enrichment)
    _fetch_ntlm_overlay() — fetches additional fields from internal REST API
    merge_dicts() — merges overlay into ES data (overlay takes precedence)
        │
        ▼
[5] Build JSON Summary
    CompanySmartpack.generate_summary() or PersonSmartpack.generate_summary()
    Constructs structured summary dict with sections:
    Company: key_information, about_company, investment_strategy, financials,
             competitors, news, leadership, board, sustainability, assignment_history
    Person:  basic_info, assignments/revenue, firm_relationships,
             recent_assignments, current_board, executive_hires
        │
        ▼
[6] OpenAI Enrichment (Person only)
    _generate_profile_summary_with_openai() — bio bullets + conversation topics
    _generate_firm_relationships_with_openai() — relationship summary bullets
    _generate_recent_assignments_from_ntlm() — formatted assignment list
    _generate_business_developments_from_ntlm() — formatted BD list
        │
        ▼
[7] PDF Content Mapping
    ConfigMapper.apply_mapping() — transforms summary dict to pdf_content dict
    using JSON path mappings from company_mapping.json / person_mapping.json
        │
        ▼
[8] PDF Generation
    generate_pdf_company() or generate_pdf_person()
    ReportLab builds multi-section PDF with tables, headers, and formatted content
    Saved to smartpackPdfMapping/generated_pdfs/
        │
        ▼
[9] Azure Storage Upload
    upload_pdf_to_storage() — uploads PDF blob to Azure Blob Storage
    Returns blob URL and blob name
        │
        ▼
[10] Download Link
    summary["smartpack_url"] = SERVER_BASE_URL + /api/download-pdf-storage/<blob_name>
    Returned to chat interface as clickable download link
```

---

## 8. PDF Generation & Storage

### PDF Structure — Company SmartPack

| Section | Content |
|---|---|
| Header | Company name, generation date |
| Key Information Table | Entity type, employees, industry, year founded, AUM/revenue, HQ, website |
| About the Company | Business overview + investment strategy |
| Indicative Portfolio | Portfolio list, financials, competitors, analyst reports |
| News | Recent headlines and summaries |
| Leadership Team | Name, title, biography |
| Board of Directors | Name, title |
| Sustainability | Rankings and report reference |
| Firm Assignment History | Assignment history table (lead consultant, position, dates) |

### PDF Structure — Person SmartPack

| Section | Content |
|---|---|
| Header | Person name, current title, generation date |
| Bio | AI-generated bullet-point biography |
| Firm # of Assignments/Revenue | Year-by-year table |
| Firm Relationships | AI-generated relationship summary bullets |
| Recent / Marquee Assignments | Completed search + consulting assignments, open counts |
| Current Board | Board/leadership analysis, recent hires, company news, conversation topics |
| Executive Directors | Table |
| Supervisory Directors | Table |

### Storage

PDFs are uploaded to Azure Blob Storage under:
- `company/<CompanyName>_smartpack.pdf`
- `person/<PersonName>_smartpack.pdf`

Download is proxied through the server at `/api/download-pdf-storage/<blob_name>` to avoid exposing storage credentials to the client.

---

## 9. Security & Guardrails

### Prompt Injection Detection

Every query passes through `prompt_injection_detector.is_prompt_injection()` before processing. Detected patterns include:

- Instruction override: "ignore previous instructions", "disregard prior context"
- Jailbreak: "developer mode", "jailbreak", "bypass filters"
- Role injection: "you are now", "act as", system/assistant token prefixes
- Secret exfiltration: "api key", "password", "send all files"
- External execution: "run", "execute", "bash", "sudo"

If injection is detected, the query is rejected with an error response.

### Credential Security

- No credentials are hardcoded anywhere in the codebase
- All secrets sourced from environment variables or Azure Key Vault
- Azure Key Vault integration via `azure-identity` (DefaultAzureCredential)
- `LOCAL_DEV=true` bypasses Key Vault for local development

### Path Traversal Prevention

PDF download endpoints validate blob names to prevent directory traversal attacks.

### Read-Only Connectors

All data source connectors expose read-only operations only. No write, update, or delete operations are implemented or exposed.

---

## 10. REST API Reference

All REST endpoints accept and return JSON.

### `POST /api/search`

Auto-routes based on intent classification.

**Request:**
```json
{ "query": "How many assignments in financial services last year?" }
```

**Response:**
```json
{
  "query": "...",
  "intent": "qna",
  "connector": "graphdb",
  "result": { ... },
  "summary": "There were 42 assignments in financial services last year..."
}
```

### `POST /api/qna`

Forces GraphDB (Neo4j) execution.

**Request:**
```json
{ "query": "List all people with an MBA from [University Name]" }
```

### `POST /api/smartpack`

Forces SmartPack generation.

**Request:**
```json
{ "query": "Generate a SmartPack for [Company Name]" }
```

**Response includes:**
```json
{
  "smartpack_url": "https://your-app.azurewebsites.net/api/download-pdf-storage/company/CompanyName_smartpack.pdf"
}
```

### `POST /api/fetch`

Fetches a document by ID from Elasticsearch.

**Request:**
```json
{ "id": "document-id-here" }
```

### `GET /api/download-pdf-storage/<blob_name>`

Downloads a SmartPack PDF from Azure Blob Storage via server proxy.

### `GET /api/download-pdf-local/<filename>`

Downloads a locally generated SmartPack PDF (fallback if storage upload fails).

---

## 11. MCP Tools Reference

The server exposes four tools via the MCP protocol, consumable by any MCP-compatible chat client (e.g., a Developer Mode-enabled custom chat).

### `search`

Auto-classifies intent and routes to the best connector.

**Parameters:**
- `query` (string): Natural language query

**Returns:** Structured result with intent, connector used, raw data, and AI summary.

### `qna`

Forces a GraphDB (Neo4j) Cypher query. Best for relationship lookups, counts, lists, and graph traversals.

**Parameters:**
- `query` (string): Natural language question about graph data

### `smartpack`

Forces SmartPack generation via Elasticsearch. Best for generating company or person dossiers.

**Parameters:**
- `query` (string): Request including entity name (e.g., "Create a SmartPack for [Company Name]")

**Returns:** Summary JSON with `smartpack_url` for PDF download.

### `fetch`

Retrieves a document by ID.

**Parameters:**
- `id` (string): Document ID

---

## 12. Configuration Reference

### `config/mcp_config.json`

Controls OpenAI prompts and model behavior:

| Key | Description |
|---|---|
| `server_instructions` | Top-level MCP server description shown to the chat client |
| `openai.classify_intent` | System prompt + user template for intent classification |
| `openai.classify_connector` | Prompt for connector selection |
| `openai.generate_request.graphdb` | Prompt for Cypher query generation |
| `openai.generate_request.elasticsearch` | Prompt for ES DSL generation |
| `openai.generate_request.databricks` | Prompt for SQL generation |
| `degrees_top_list` | Canonical degree list for fuzzy education query matching |

### `config/intents.json`

Controls SmartPack Elasticsearch queries:

| Key | Description |
|---|---|
| `smartpack.companySmartpack.indexes` | ES indexes to search for company SmartPacks |
| `smartpack.companySmartpack.searchField` | Field to match company name against |
| `smartpack.companySmartpack.source` | Fields to retrieve from ES |
| `smartpack.personSmartpack.indexes` | ES indexes to search for person SmartPacks |
| `smartpack.personSmartpack.searchField` | Field to match person name against |

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `LOCAL_DEV` | No | Set `true` to skip Azure Key Vault |
| `OPENAI_API_KEY` | Yes* | OpenAI API key (*or Azure OpenAI vars) |
| `AZ_COGNITIVE_URL` | Yes* | Azure OpenAI endpoint (*if using Azure) |
| `API_VERSION` | Yes* | Azure OpenAI API version |
| `GPT_MODEL_NAME` | Yes | Model name (e.g., `gpt-4o-mini`) |
| `ELASTIC_URL` | Yes | Elasticsearch base URL |
| `ELASTIC_USER` | No | Elasticsearch username |
| `ELASTIC_PASSWORD` | No | Elasticsearch password |
| `NEO4J_URL` | Yes | Neo4j Bolt URL |
| `NEO4J_USER` | Yes | Neo4j username |
| `NEO4J_PASSWORD` | Yes | Neo4j password |
| `DATABRICKS_HOST` | No | Databricks workspace URL |
| `DATABRICKS_TOKEN` | No | Databricks PAT |
| `DATABRICKS_SQL_ENDPOINT_ID` | No | Databricks SQL endpoint ID |
| `NTLM_USERNAME` | No | NTLM username |
| `NTLM_PASSWORD` | No | NTLM password |
| `NTLM_COMPANY_PATH` | No | NTLM company enrichment URL |
| `NTLM_PERSON_PATH` | No | NTLM person enrichment URL |
| `AZURE_STORAGE_CONNECTION_STRING` | No | Azure Blob Storage connection string |
| `AZURE_STORAGE_CONTAINER_NAME` | No | Blob container name for PDFs |
| `KEY_VAULT_NAME` | No | Azure Key Vault name (production) |
| `SERVER_BASE_URL` | Yes | Public base URL for PDF download links |
| `SMARTPACK_BACKENDS` | No | `elastic`, `databricks`, or `elastic,databricks` |
| `SMARTPACK_PRIMARY` | No | Primary backend when multiple are configured |
| `GRAPHDB_SCHEMA_DB` | No | Neo4j database to introspect for schema (default: `neo4j`) |
| `GRAPH_SCHEMA_TTL_SECONDS` | No | Schema cache TTL in seconds (default: `900`) |
| `DEFAULT_LIST_LIMIT` | No | Default result limit for list queries (default: `100`) |

---

## 13. Prompting Guide

This section guides users on how to ask questions effectively in the chat interface to get the best results.

### General Principles

- Be specific about what you want — the more context you give, the better the query
- Use entity names as they appear in the data (full company names, full person names)
- For SmartPacks, explicitly say "create", "generate", "compile", or "SmartPack"
- For data lookups, ask naturally — the system handles routing automatically

---

### QnA Queries (Graph Database)

These queries search the knowledge graph for relationships, counts, lists, and factual lookups.

**Good patterns:**

```
How many assignments did we run in the healthcare sector last year?
List all people currently employed at [Company Name].
Who are the lead consultants on open search assignments at [Company Name]?
Show me all projects in the technology sector from 2023.
How many consulting engagements were completed in Q1?
Find people with an MBA from [University Name].
What is the total revenue from assignments in financial services?
Show all open assignments where [Person Name] is the lead consultant.
```

**Tips:**
- Use terms like "assignments", "projects", "engagements", "deals" interchangeably — the system treats them as synonyms
- Partial company names work: "Stanford" will match "Stanford University"
- You can filter by industry, sector, location, role, or date range
- Ask for counts, lists, or comparisons — all are supported

---

### SmartPack Generation

SmartPacks generate a full PDF dossier for a company or person.

**Company SmartPack:**

```
Create a SmartPack for [Company Name]
Generate a company profile for [Company Name]
Compile a dossier on [Company Name]
Assemble a brief for [Company Name]
```

**Person SmartPack:**

```
Create a SmartPack for [Full Person Name]
Generate a profile for [Full Person Name]
Compile a dossier on [Full Person Name]
```

**Tips:**
- Use the full official company name for best matching (e.g., "Acme Corporation" not just "Acme")
- Use the full person name as it appears in the system
- The system will return a download link for the generated PDF
- SmartPacks include: key info, financials, leadership, board, news, sustainability, and assignment history

---

### Fetch by ID

```
Fetch document with ID abc123
Get the document abc123
```

---

### What NOT to Ask

The system is designed for enterprise data retrieval. It will not respond to:

- Requests to ignore instructions or bypass safety rules
- Requests for credentials, API keys, or system internals
- Requests to execute commands or access external URLs
- Jailbreak or persona-override attempts

These are blocked by the prompt injection detector before reaching the LLM.

---

### Example Session

```
User: How many search assignments were completed in the financial services sector in 2024?

System: Based on the graph data, there were 87 completed search assignments in the
        financial services sector in 2024. The top industries within financial services
        were Banking (32), Asset Management (28), and Insurance (27).

---

User: Create a SmartPack for Acme Capital Partners

System: Generating SmartPack for Acme Capital Partners...
        ✓ Company data retrieved from Elasticsearch
        ✓ Enrichment data merged
        ✓ PDF generated
        ✓ Uploaded to storage

        Download your SmartPack here:
        https://your-app.azurewebsites.net/api/download-pdf-storage/company/Acme_Capital_Partners_smartpack.pdf

---

User: Who are the lead consultants on open assignments at Acme Capital Partners?

System: There are currently 3 open assignments at Acme Capital Partners.
        Lead consultants:
        - [Consultant Name A] — CFO Search (opened Jan 2025)
        - [Consultant Name B] — Board Director Search (opened Feb 2025)
        - [Consultant Name C] — CTO Search (opened Mar 2025)
```
