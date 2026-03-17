# MCP Server + Flask (Option A) --- Local Development & Azure Deployment

This project provides an **MCP server** mounted at `/sse` inside an
**ASGI** app (Starlette), and a **Flask API** with routes such as `/`,
`/api/search`, `/api/fetch`. It supports both **local OpenAI API key
mode** and **Azure OpenAI** (Azure AI Foundry) mode depending on
environment variables.

## 🚀 Local Development Setup

### 1. Clone the repository

``` bash
git clone <your-repo-url>
cd <repo-folder>
```

### 2. Create and activate a Python virtual environment

#### Mac / Linux

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows (PowerShell)

``` bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

``` bash
pip install -r requirements.txt
```

### 4. Create a `.env` file

``` env
LOCAL_DEV=true
OPENAI_API_KEY=your_openai_key_here
GPT_MODEL_NAME=gpt-4o-mini

ELASTIC_URL=http://localhost:9200
ELASTIC_USER=elastic
ELASTIC_PASSWORD=changeme

NEO4J_URL=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=yourpassword
```

### 5. Start the server with Uvicorn

``` bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

## ☁️ Azure Deployment

### Environment Variables

    API_VERSION
    AZ_COGNITIVE_URL
    COGNITIVE_SUBSCRIPTION_KEY
    OPENAI_API_KEY (optional if using OpenAI)

### Startup Command

    gunicorn -k uvicorn.workers.UvicornWorker server:app --bind 0.0.0.0:$PORT
