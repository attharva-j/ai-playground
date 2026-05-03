# ALO Yoga RAG System

A production-grade Retrieval-Augmented Generation system for ALO Yoga, enabling natural language querying across three knowledge domains: **product knowledge**, **policy & operations intelligence**, and **customer context**.

## Architecture

The system follows a pipeline pattern:

**Ingestion → Query Intelligence → Hybrid Retrieval → Generation → Evaluation**

Key capabilities:

- **Per-domain chunking** — one chunk per product; semantic section-based chunking for policies
- **Hybrid retrieval** — dense (ChromaDB + voyage-3) and sparse (BM25) search with RRF fusion and cross-encoder reranking
- **Query intelligence** — LLM-based intent routing, HyDE for policy queries, multi-query decomposition, scope guard
- **Faithfulness guardrail** — second LLM call verifies claims against source context, with automatic regeneration
- **Structured customer lookup** — customer data accessed by exact ID match, not embedded
- **Incremental index refresh** — SHA-256 content-addressed registry re-embeds only changed chunks
- **Full observability** — structured trace logs at every pipeline stage

## Prerequisites

- Python 3.12+
- An [OpenAI API key](https://platform.openai.com/) (for GPT-4o generation and GPT-4.1-nano intent routing)
- A [Voyage AI API key](https://www.voyageai.com/) (for voyage-3 embeddings)

## Setup

1. **Clone and navigate to the project:**

   ```bash
   cd alo-rag
   ```

2. **Create a virtual environment and install dependencies:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

3. **Set up environment variables:**

   Copy the example file and fill in your API keys:

   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your keys:

   ```
   OPENAI_API_KEY=your-openai-api-key
   VOYAGE_API_KEY=your-voyage-api-key
   ```

## Data

Source data lives in `data/` with three subdirectories:

| Directory | Contents |
|---|---|
| `data/products/` | `alo_product_catalog.json` — product catalog with SKUs, fabrics, sizing, care instructions |
| `data/policies/` | Markdown policy documents — returns, shipping, loyalty program, promotions |
| `data/customers/` | `customer_order_history.json` — 8 synthetic customer profiles with order histories |

See `data/README.md` for detailed descriptions of each data file and the intentional retrieval challenges built into the dataset.

## Running the Ingestion Pipeline

The ingestion pipeline loads source data, chunks it using domain-specific strategies, computes embeddings, and builds the ChromaDB and BM25 indexes.

```bash
cd alo-rag
python -m src.ingestion.run_ingestion --data-dir data
```

**Options:**

| Flag | Description | Default |
|---|---|---|
| `--data-dir` | Root data directory | `data` |
| `--persist-dir` | ChromaDB persistence directory | In-memory |
| `--registry-db` | Path to SQLite registry database | `<data-dir>/registry.db` |
| `-v`, `--verbose` | Enable DEBUG-level logging | INFO |

**Example with persistence:**

```bash
python -m src.ingestion.run_ingestion --data-dir data --persist-dir data/chroma_db -v
```

The pipeline prints a summary on completion showing records ingested, chunks created, embeddings computed, and registry statistics.

## Launching the Demo UI

The demo consists of a Python FastAPI backend (streaming RAG API) and a Next.js chat frontend built with [assistant-ui](https://www.assistant-ui.com/).

### 1. Start the Python backend

```bash
cd alo-rag
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

The server initialises the full RAG pipeline on startup (loading models, computing embeddings, building indexes). First launch may take 30–60 seconds.

### 2. Start the Next.js frontend

```bash
cd alo-rag/demo
npm install   # first time only
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

**Features:**

- **Streaming chat** — real-time token-by-token streaming from the OpenAI API via Server-Sent Events
- **Customer selector** — dropdown populated from the customer data file; personalises queries with order history
- **Multi-turn conversation** — follow-up questions resolve references from prior turns in the same session
- **Pipeline trace panel** — toggle to inspect intent classification, retrieval scores, HyDE activation, and stage latencies
- **Suggested prompts** — quick-start suggestions for common ALO Yoga questions
- **Markdown rendering** — formatted responses with headings, lists, and code blocks

> **Note:** Both the Python backend and Next.js frontend must be running simultaneously. The frontend proxies chat requests to the backend at `http://localhost:8000`.

## Running Tests

The test suite uses pytest and covers all pipeline components:

```bash
cd alo-rag
pytest
```

**With coverage:**

```bash
pytest --cov=src --cov-report=term-missing
```

**Run a specific test file:**

```bash
pytest tests/test_pipeline.py -v
```

## Running the Evaluation Suite

The evaluation framework runs 25 test queries (easy, medium, hard) through the pipeline and computes retrieval metrics (Recall@5, MRR, Context Precision) and generation metrics (Faithfulness, Answer Relevance, Hallucination Rate).

```bash
cd alo-rag
python -m src.eval
```

Test queries are defined in `evals/test_queries.json`. The harness also includes:

- **Failure analysis** — identifies the 3 worst-performing queries with detailed diagnostics
- **Regression harness** — compares current results against a stored baseline to detect improvements and regressions

## Project Structure

```
alo-rag/
├── data/                          # Source data
│   ├── products/                  #   Product catalog JSON
│   ├── policies/                  #   Policy markdown documents
│   └── customers/                 #   Customer order history JSON
├── demo/                          # Next.js chat frontend
│   ├── app/                       #   Next.js app router pages
│   │   ├── api/chat/route.ts      #     Proxy endpoint to Python backend
│   │   ├── globals.css            #     Tailwind CSS theme
│   │   ├── layout.tsx             #     Root layout
│   │   └── page.tsx               #     Main chat page
│   ├── components/
│   │   └── assistant-ui/
│   │       └── thread.tsx         #   Chat thread component
│   ├── lib/
│   │   └── utils.ts               #   Utility functions
│   ├── package.json               #   Node.js dependencies
│   └── README.md                  #   Frontend-specific docs
├── docs/
│   ├── ADR.md                     # Architecture Decision Record
│   ├── CHANGELOG.md               # Architecture changelog (chronological)
│   ├── failure_analysis.md        # Failure analysis for worst-performing queries
│   └── production_readiness_memo.md  # Production readiness assessment
├── evals/
│   └── test_queries.json          # 25 evaluation test queries
├── server.py                      # FastAPI backend (streaming RAG API)
├── src/
│   ├── ingestion/                 # Data loading, chunking, embedding, indexing
│   │   ├── loaders.py             #   Product, policy, and customer loaders
│   │   ├── chunkers.py            #   Per-domain chunking strategies
│   │   ├── embedders.py           #   Embedding service (voyage-3 + fallback)
│   │   ├── index_builder.py       #   ChromaDB and BM25 index construction
│   │   ├── registry.py            #   Document registry for incremental refresh
│   │   └── run_ingestion.py       #   CLI ingestion runner
│   ├── query/                     # Query intelligence layer
│   │   ├── intent_router.py       #   LLM-based intent classification
│   │   ├── hyde.py                #   Hypothetical Document Embeddings
│   │   ├── decomposer.py          #   Multi-query decomposition
│   │   └── scope_guard.py         #   Out-of-scope detection
│   ├── retrieval/                 # Hybrid retrieval engine
│   │   ├── hybrid_search.py       #   Dense + sparse search orchestration
│   │   ├── fusion.py              #   Reciprocal Rank Fusion (RRF)
│   │   └── reranker.py            #   Cross-encoder reranking
│   ├── generation/                # Answer generation
│   │   ├── llm_client.py          #   OpenAI GPT wrapper
│   │   ├── prompt_builder.py      #   Structured prompt construction
│   │   ├── customer_context.py    #   Customer data structured lookup
│   │   └── guardrails.py          #   Faithfulness verification + regeneration
│   ├── eval/                      # Evaluation framework
│   │   ├── harness.py             #   Eval harness and test query loading
│   │   ├── metrics.py             #   Retrieval and generation metrics
│   │   ├── failure_analysis.py    #   Worst-query failure analysis
│   │   └── regression.py          #   Regression comparison harness
│   ├── models.py                  # Core data models and types
│   └── pipeline.py                # Pipeline orchestrator
├── tests/                         # Unit and integration tests
├── pyproject.toml                 # Project configuration and dependencies
└── .env.example                   # Environment variable template
```

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.12+ |
| LLM | OpenAI GPT (GPT-4o for generation, GPT-4.1-nano for classification) |
| Embeddings | Voyage AI voyage-3 (primary), sentence-transformers/all-mpnet-base-v2 (fallback) |
| Vector Store | ChromaDB |
| Sparse Retrieval | rank-bm25 |
| Reranker | BAAI/bge-reranker-base |
| Backend API | FastAPI + Uvicorn |
| Frontend | Next.js 15, React 19, Tailwind CSS 4 |
| Chat UI | assistant-ui (AI SDK compatible) |
| Evaluation | Custom deterministic retrieval metrics + LLM-as-judge generation metrics |
| Data Validation | Pydantic |

## Implemented vs Planned

### Implemented Now

- Per-domain chunking (product, policy) with fabric glossary entity chunks
- Hybrid dense/BM25 retrieval with RRF fusion
- Cross-encoder reranking (BAAI/bge-reranker-base) with min_score filtering
- Adaptive retrieval depth (final_k=3 single-domain, final_k=4 multi-domain)
- LLM-based intent routing (GPT-4.1-nano) with scope guard
- HyDE for policy queries (GPT-4o-mini)
- Parallel HyDE + decomposition via ThreadPoolExecutor
- Structured customer lookup (not embedded)
- Pre-generation answerability gate for customer/policy queries
- Faithfulness guardrail with regeneration (eval harness only)
- Multi-turn conversation context (last 3 exchanges)
- Incremental ingestion via DocumentRegistry (SHA-256 content hashing)
- True token-by-token streaming from OpenAI API
- Custom evaluation harness with deterministic retrieval + LLM-as-judge generation metrics
- Smoke and full eval modes with regression comparison
- Next.js chat UI with pipeline trace panel

### Planned / Production Extension

- ONNX reranker export (deps added, export instructions documented)
- Semantic response cache with DocumentRegistry-tied invalidation
- Managed vector database (Pinecone, Weaviate) replacing in-memory ChromaDB
- Event-driven incremental indexing (S3/CMS webhook triggers)
- Production auth/authN integration
- Query-aware conversation rewriting for retrieval
- NLI-based faithfulness verification (replacing LLM-as-judge)
- Human feedback loop for retrieval quality improvement
- Bitemporal policy metadata for seasonal/versioned policy retrieval
- Online monitoring and alerting dashboard

## Documentation

- **[Architecture Decision Record](docs/ADR.md)** — key technical decisions and their rationale (chunking, embeddings, HyDE, customer data, prompt architecture, reranker selection)
- **[Architecture Changelog](docs/CHANGELOG.md)** — chronological record of every significant architectural change with reasoning
- **[Failure Analysis](docs/failure_analysis.md)** — detailed root-cause analysis of the worst-performing evaluation queries
- **[Production Readiness Memo](docs/production_readiness_memo.md)** — operational risks, mitigation strategies, latency budget, and observability plan
