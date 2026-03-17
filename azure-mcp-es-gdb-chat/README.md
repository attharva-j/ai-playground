# Azure MCP ES-GDB Chat

## Business Use Case

Enterprise knowledge workers spend significant time manually searching across disconnected data systems — a graph database holding relationship and assignment history, an Elasticsearch cluster holding company and person profiles, and a Databricks warehouse holding structured analytics — to answer questions or compile executive briefings. This friction slows decision-making and creates inconsistency in how information is surfaced and presented.

This project solves that problem by exposing a single, intelligent MCP (Model Context Protocol) server that sits behind a Developer Mode-enabled custom chat interface. Users ask questions in natural language; the server classifies intent, routes to the right data source, generates the appropriate query, executes it, and returns a coherent, AI-summarized answer — or a fully formatted PDF SmartPack — without the user ever needing to know which system holds the data.

### Value & Impact

- Eliminates manual cross-system lookups for relationship intelligence, company profiles, and assignment history
- Reduces time-to-insight from hours to seconds for research and briefing workflows
- Standardizes how executive profiles and company dossiers are generated and distributed
- Provides a secure, auditable, prompt-injection-resistant interface over sensitive enterprise data
- Enables non-technical users to query graph and search infrastructure through plain English

---

## Project Structure

```
azure-mcp-es-gdb-chat/
├── server.py                          # ASGI entry point (Starlette + Uvicorn)
├── mcp_app.py                         # MCP server + Flask REST API
├── server_search.py                   # Legacy MCP server (reference)
├── utils.py                           # Core utilities and connector helpers
├── prompt_injection_detector.py       # Heuristic prompt-injection guardrail
├── degree_resolver.py                 # Fuzzy degree/field-of-study matching
├── prop_resolver.py                   # Graph property name resolution + schema cache
├── config/
│   ├── mcp_config.json               # OpenAI prompts, model config, connector templates
│   └── intents.json                  # SmartPack Elasticsearch query templates
├── DataSourceConnectors/
│   ├── graphdb_connector.py          # Neo4j Bolt driver wrapper
│   ├── elasticsearch_connector.py    # Elasticsearch HTTP client
│   ├── databricks_connector.py       # Databricks REST API (SQL + DBFS)
│   └── ntlm_rest_connector.py        # NTLM-authenticated REST connector
├── Mapping/
│   ├── smartpack_entities.py         # CompanySmartpack + PersonSmartpack logic
│   ├── config_mapper.py              # JSON-driven data-to-PDF transformation
│   └── mapping_configs/
│       ├── company_mapping.json      # Company PDF content mapping
│       └── person_mapping.json       # Person PDF content mapping
├── smartpackPdfMapping/
│   └── smartpack_generator.py        # ReportLab PDF generation
├── requirements.txt
├── procfile                          # Gunicorn startup command
└── host.json                         # Azure Functions config (if applicable)
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Access to Neo4j, Elasticsearch, and/or Databricks instances
- Azure OpenAI or OpenAI API key
- (Optional) Azure Key Vault and Azure Blob Storage

### Local Setup

```bash
# 1. Clone and enter the directory
git clone <your-repo-url>
cd azure-mcp-es-gdb-chat

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env_sample .env
# Edit .env with your credentials (see Environment Variables below)

# 5. Start the server
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

```env
# Local development flag (skips Azure Key Vault)
LOCAL_DEV=true

# OpenAI / Azure OpenAI
OPENAI_API_KEY=your_key_here
GPT_MODEL_NAME=gpt-4o-mini
# For Azure OpenAI:
AZ_COGNITIVE_URL=https://<resource>.openai.azure.com/
API_VERSION=2024-02-01

# Elasticsearch
ELASTIC_URL=https://your-es-host:9200
ELASTIC_USER=elastic
ELASTIC_PASSWORD=changeme

# Neo4j / GraphDB
NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=yourpassword

# Databricks (optional)
DATABRICKS_HOST=https://<workspace>.azuredatabricks.net
DATABRICKS_TOKEN=your_pat_token
DATABRICKS_SQL_ENDPOINT_ID=your_endpoint_id

# NTLM REST (optional enrichment layer)
NTLM_USERNAME=domain\user
NTLM_PASSWORD=yourpassword
NTLM_COMPANY_PATH=https://internal-api/company
NTLM_PERSON_PATH=https://internal-api/person

# Azure Storage (for PDF uploads)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_STORAGE_CONTAINER_NAME=smartpacks

# Azure Key Vault (production)
KEY_VAULT_NAME=your-keyvault-name

# Server base URL (for PDF download links)
SERVER_BASE_URL=https://your-app.azurewebsites.net
```

---

## Azure Deployment

### App Service (Linux)

1. Push code to your Azure App Service
2. Set all environment variables in **Configuration > Application Settings**
3. Set the startup command:

```
gunicorn -k uvicorn.workers.UvicornWorker server:app --bind 0.0.0.0:$PORT
```

### Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/mcp` | SSE | MCP SSE transport |
| `/sse` | HTTP | MCP Streamable HTTP transport |
| `/api/search` | POST | Auto-routed search (intent-aware) |
| `/api/qna` | POST | Force GraphDB QnA |
| `/api/smartpack` | POST | Force SmartPack generation |
| `/api/fetch` | POST | Fetch document by ID |
| `/api/download-pdf-storage/<blob>` | GET | Download PDF from Azure Storage |
| `/api/download-pdf-local/<filename>` | GET | Download locally generated PDF |

---

## MCP Tools

The server exposes four MCP tools consumable by any MCP-compatible chat client:

| Tool | Description |
|---|---|
| `search` | Auto-classifies intent and routes to the best connector |
| `qna` | Forces a GraphDB (Neo4j) Cypher query |
| `smartpack` | Forces a SmartPack profile generation via Elasticsearch |
| `fetch` | Retrieves a document by ID |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| fastmcp | 2.13.0.2 | MCP server framework |
| starlette | 0.50.0 | ASGI framework |
| flask | 3.1.2 | REST API |
| uvicorn | 0.38.0 | ASGI server |
| gunicorn | 23.0.0 | Production WSGI/ASGI server |
| openai | 2.7.1 | LLM intent classification + summarization |
| neo4j | latest | Graph database driver |
| requests | 2.32.4 | HTTP client |
| reportlab | 4.0+ | PDF generation |
| azure-identity | 1.25.1 | Azure authentication |
| azure-keyvault-secrets | 4.10.0 | Secrets management |
| azure-storage-blob | latest | PDF blob storage |
| requests-ntlm | latest | NTLM authentication |
| python-dotenv | 1.2.1 | Local env file loading |

---

## Security

- Prompt injection detection via heuristic regex patterns (`prompt_injection_detector.py`)
- All credentials sourced from environment variables or Azure Key Vault — no hardcoded secrets
- Path traversal prevention on PDF download endpoints
- Read-only connector interfaces (no write operations exposed)
- NTLM and TLS support for internal enterprise REST APIs
