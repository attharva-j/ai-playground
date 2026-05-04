# ALO RAG System — Solution Overview

## Solution Introduction & Architecture Overview

Thanks for the interesting problem statement. Every AI use case is different, and I genuinely enjoy finding ways to tailor solutions to each one, especially in retail. Retail systems have so much variation across products, policies, seasons, customer journeys, discounts, loyalty programs, and operational edge cases. 🛍️✨

For this case study, I wanted to build something closer to an enterprise-ready AI product POC rather than a simple "embed, retrieve, answer" demo. The goal was not just to answer questions, but to answer them **with the right evidence**, **from the right source**, and sometimes to know when **not to answer** until more context is available. That's where a lot of practical AI engineering lives: designing systems that are useful, grounded, measurable, and honest about uncertainty. 🙂

---

## 1. Introduction to the Use Case

ALO's case study focuses on a very real enterprise GenAI problem: multiple teams have started building RAG systems and knowledge assistants independently, but there is no shared quality bar for chunking, retrieval, evaluation, reliability, or production-readiness.

The assignment was to design, build, and evaluate a **production-grade RAG system for retail** across three major knowledge domains:

#### 📦 Product Knowledge

Product specs, materials, fabric types, sizing, care instructions, product attributes, and restocking-related information.

#### 📋 Policy & Operations Intelligence

Return policies, shipping SLAs, promo eligibility, loyalty-tier logic, sale restrictions, seasonal policy changes, and compliance-sensitive rules.

#### 👤 Customer Context Queries

Customer-specific questions like "What did I buy last season?" or "Is my item eligible for return?" — blending retrieved knowledge with exact structured customer data.

### What the assignment expected

The deliverable was expected to cover four independently scored areas:

| Area | What was expected |
|------|-------------------|
| **RAG System Implementation** | End-to-end pipeline, multiple data types, embeddings, vector store, retrieval beyond naive top-k, generation layer, and working demo interface |
| **Architecture Decision Record** | Clear reasoning for chunking, embedding model, retrieval strategy, prompt design, and what would change with more time/data |
| **Evaluation Framework** | At least 20 test queries, retrieval metrics, generation metrics, failure analysis, and a regression harness |
| **Production Readiness Memo** | Risks and mitigations for staleness, retrieval failures, latency, guardrails, out-of-scope queries, and observability |

### Key constraints

| Constraint | Design implication |
|------------|-------------------|
| **Open-ended stack** | Freedom to choose tools, but every choice needed justification |
| **Use any LLM provider** | Optimize for quality, cost, or local fallback depending on the stage |
| **Build synthetic data** | Product, policy, and customer datasets had to be representative enough for evaluation |
| **Time-boxed to ~20–24 hours** | The solution needed to be focused, not overbuilt |
| **Runnable repo + docs** | A reviewer should be able to run the demo and evals without reverse-engineering the project |
| **Evaluation heavily weighted** | The system had to expose its own failures, not hide them |

### My framing

> **Design Philosophy**
> I treated this as a **retail AI platform problem**, not just a chatbot problem.

- Retail questions are not all the same
- Customer data should not be semantically embedded
- Retrieval should be domain-aware
- Safe "I need more context" > confident hallucination
- Evaluation should catch real failures

---

## 2. ADR Summary

The detailed ADR is available at `docs/ADR.md`. Below is a condensed decision summary.

| # | Decision Area | Chosen | Reason | Alt #1 | Alt #2 | Alt #3 |
|---|---------------|--------|--------|--------|--------|--------|
| 1 | Chunking strategy | Domain-aware chunking: product, fabric entity, section-based policy chunks | Domains need different boundaries | Fixed token windows — splits rules | One giant document — too noisy | Semantic-only — less deterministic |
| 2 | Fabric knowledge | First-class fabric glossary chunks | Fabric comparisons need entity evidence | Product-only chunks — scattered evidence | Manual FAQ — hard to scale | LLM summaries — harder to verify |
| 3 | Policy chunking | Section-based with tags | Preserves conditional policy logic | Small sliding windows — breaks clauses | Whole policy doc — too much noise | Rule engine — too heavy for POC |
| 4 | Embedding model | `voyage-3` primary + `all-mpnet-base-v2` fallback | Quality first, graceful fallback | OpenAI embeddings — good but not primary | Local-only — lower ceiling | Cohere — future option |
| 5 | Vector store | ChromaDB for local POC | Fast local iteration, simple setup | Pinecone — external dependency | Weaviate — more infra | OpenSearch — better prod target |
| 6 | Sparse retrieval | BM25 in-memory index | Captures exact retail terms | Dense-only — misses SKUs | SQL LIKE — too limited | Keyword rules — brittle |
| 7 | Fusion strategy | Reciprocal Rank Fusion (RRF) | Combines rankings without calibration | Weighted score fusion — needs normalization | Dense priority — misses lexical | BM25 priority — weak paraphrase |
| 8 | Reranking | Cross-encoder reranker | Improves final context ordering | No reranker — noisy context | LLM reranking — more latency | Manual rules — hard to generalize |
| 9 | Metadata filtering | Hard domain filters for clear queries | Improves context precision | Soft boosting — passes noise | Always broad — hallucination risk | User-selected — worse UX |
| 10 | Query intelligence | Intent routing, HyDE, decomposition selectively | Better retrieval for hard queries | Always HyDE — slower, costly | No expansion — misses nuance | Multi-agent — too heavy |
| 11 | Customer data | Structured JSON lookup by `customer_id` | Exact facts beat semantic search | Embed customer data — privacy risk | SQL database — more setup | LLM memory — not deterministic |
| 12 | Answerability gate | Pre-generation evidence check | Prevents unsupported answers | Prompt-only — too easy to ignore | Post-hoc correction — too late | Always answer — unsafe |
| 13 | Prompt architecture | Context-bound prompt with chunk IDs | Grounding and citations matter | Free-form — less controllable | Huge context stuffing — more noise | Tool-agent — more complex |
| 14 | LLM for generation | GPT-4o-style quality model | Strong answer quality and reasoning | Small local LLM — lower quality | GPT-4.1-nano — cheaper but weaker | Claude/Bedrock — valid future |
| 15 | Faithfulness guardrail | LLM-as-judge with fail-closed behavior | Safer high-risk answers | No guardrail — hallucination risk | RAGAS only — less domain-specific | Local NLI — good future optimization |
| 16 | Evaluation metrics | Custom retrieval + judge + behavior metrics | Domain-specific scoring needed | RAGAS defaults — less retail-specific | DeepEval — less control | Manual review — not scalable |
| 17 | Behavior-aware eval | Clarify/refuse scored separately | Safe behavior is success | Treat all as QA — punishes refusal | Ignore safety — incomplete | Human-only — slow loop |
| 18 | Staleness handling | DocumentRegistry with content hashes | Tracks changes incrementally | Full reindex — expensive | No registry — drift risk | CMS-only sync — out of scope |
| 19 | Demo interface | React/Next.js chat UI with assistant-ui | Better UX, minimal extra effort | Streamlit — less polished | CLI only — weak demo | Notebook — less product-like |
| 20 | UI effort | Next.js + assistant-ui + backend API | Chat UI in ~40–45 mins | Build from scratch — unnecessary | Heavy design system — overkill | No trace panel — less explainable |
| 21 | Observability | Trace logs with decisions and latency | Debuggable and evaluator-friendly | Print-only — hard to inspect | External APM — too much setup | No trace — black-box demo |
| 22 | Production path | Local POC, AWS-friendly design | Practical now, scalable later | Full cloud now — too much for timebox | Local-only thinking — weak prod story | Serverless-only — may constrain retrieval |

The biggest design decision was to **avoid treating this as one generic RAG pipeline**. Instead, the solution uses domain-specific retrieval and safety logic: product questions use product/fabric evidence, policy questions use tagged policy sections, customer questions use exact structured lookup, missing context triggers clarification, out-of-scope questions are refused deterministically, and evaluation separates answerable QA from expected safe behavior.

---

## 3.1 Architecture Diagram

The diagram below gives a high-level view of how the current system is wired.

> *See `solution_overview.html` for the interactive architecture diagram and query flow visualization.*

**Figure 1** — End-to-end system architecture. Hover nodes for details. Use buttons to trace data flow paths (Request Path, Retrieval, Generation, Ingestion, Customer, Eval).

### What this architecture achieves

- **Understand the query** — Is this product, policy, customer, cross-domain, or out-of-scope?
- **Check if answering is allowed** — Does the system actually have the required evidence?
- **Retrieve the right evidence** — Dense search, keyword search, metadata filtering, reranking, fabric chunks, and companion policy chunks.
- **Generate only from context** — Build a controlled prompt with source-aware context.
- **Verify and trace the response** — Check faithfulness, expose evidence, and log decisions for debugging/evaluation.

### Key innovations beyond baseline RAG

Several components in this system go beyond a standard embed-retrieve-generate pipeline. Each one addresses a specific failure mode observed in retail QA.

#### 🔀 Reciprocal Rank Fusion (RRF)

Merges dense and sparse retrieval rankings without needing score calibration, so BM25 exact-match results and semantic results contribute equally.

> *Reference: Cormack et al., SIGIR 2009 — Original RRF paper*

#### 🔍 HyDE (Hypothetical Document Embeddings)

Generates a hypothetical answer first, then embeds it for retrieval, closing the vocabulary gap between short user queries and long policy documents.

> *Reference: Gao et al., 2022 — HyDE paper on arXiv*

#### ⚖️ Cross-Encoder Reranking

A second-stage BAAI/bge-reranker-base model jointly scores query-chunk pairs, dramatically improving precision over first-stage bi-encoder retrieval alone.

> *Reference: BAAI/bge-reranker-base on HuggingFace*

#### 🧭 Intent-Aware Routing

A lightweight LLM classifier (GPT-4.1-nano) routes queries to domain-specific retrieval paths before search begins, reducing irrelevant context by filtering at the intent level.

> *Reference: OpenAI Text Generation docs*

#### 🛡️ Faithfulness Guardrail (LLM-as-Judge)

A second LLM call verifies that every claim in the generated answer is supported by retrieved evidence, with fail-closed behavior for high-risk policy and customer responses.

> *Reference: Zheng et al., 2023 — LLM-as-Judge paper*

#### 🚦 Answerability Gate

A pre-generation evidence check that refuses to answer when required context is missing, turning "I don't know" into a first-class system behavior instead of a hallucination risk.

> *Reference: Asai et al., 2024 — Self-RAG: adaptive retrieval*

#### 🧬 Domain-Aware Chunking

Products, fabrics, and policies each get purpose-built chunking strategies that preserve business-meaningful boundaries instead of splitting on arbitrary token windows.

> *Reference: Pinecone — Chunking strategies guide*

#### 📊 Behavior-Aware Evaluation

Clarification and refusal responses are scored as behavior success rather than retrieval failure, preventing the eval harness from penalizing the system for being safely cautious.

> *Reference: RAGAS — RAG evaluation framework docs*

---

## 3.2 Query Flow

This flowchart shows how a user query travels through the system.

> *See `solution_overview.html` for the interactive architecture diagram and query flow visualization.*

**Figure 2** — Query flow from user question to final answer, showing all decision gates.

> "What kind of question is this, what evidence is required, do I have that evidence, and only then — what should I answer?"
>
> — The design philosophy in one sentence

---

## What this solution emphasizes

- Grounded answers over fluent guesses
- Structured customer lookup over semantic search
- Retail-specific retrieval over generic top-k
- Evaluation that catches real failures
- Safe clarification/refusal as a valid outcome
- Traceability for reviewers and production monitoring

> **POC with production DNA**
> This is still a POC, but the architecture is intentionally shaped like something that can grow into a production-grade AI capability.

---

## 4. How the Solution Maps to Evaluation Criteria

Each requirement has a short explanation and a direct pointer to where it is implemented or documented.

### 4.1 RAG System Implementation

| Requirement | How addressed | Where to look |
|-------------|---------------|---------------|
| **Functional end-to-end RAG pipeline** | Accepts query, routes by intent, retrieves evidence, checks answerability, generates answer, records trace data | `src/pipeline.py` |
| **Multiple data/document types** | Product catalog JSON, policy documents, structured customer order JSON — each handled differently | `loaders.py`, `chunkers.py` |
| **Embedding and vector store** | `voyage-3` primary with `all-mpnet-base-v2` fallback, ChromaDB for dense retrieval | `embedders.py` |
| **Retrieval beyond naive top-k** | Dense + BM25, RRF fusion, metadata filtering, fabric/entity boosting, companion policy expansion, cross-encoder reranking | `hybrid_search.py` |
| **Prompt architecture** | Injects retrieved chunks, customer context, chat history, source IDs, and safety instructions | `prompt_builder.py` |
| **Guardrails** | Faithfulness verification with fail-closed behavior for high-risk policy/customer scenarios | `guardrails.py` |
| **Customer-context queries** | Exact structured lookup by `customer_id`, not semantic embedding. Missing context triggers clarification. | `customer_context.py` |
| **Working demo interface** | React/Next.js chat UI with trace information for debugging | `demo/app/page.tsx` |
| **Runnable setup instructions** | README covers install, ingestion, backend, demo UI, and evaluations | `README.md` |

### 4.2 Architecture Decision Record

| ADR Requirement | How addressed | Where to look |
|-----------------|---------------|---------------|
| **Chunking strategy** | Product, fabric, policy, and customer data handled differently. Product/fabric is entity-aware; policies are section-based and tag-aware. | `docs/ADR.md`, `chunkers.py` |
| **Chunk size and overlap tradeoffs** | Avoids generic fixed-size chunking where it would split product attributes or policy rules | `docs/ADR.md` |
| **Embedding model selection** | `voyage-3` choice, `all-mpnet-base-v2` fallback, and rationale documented | `docs/ADR.md`, `embedders.py` |
| **Retrieval approach** | Hybrid retrieval, RRF fusion, metadata filtering, reranking, fabric boosts, and policy companion chunks | `docs/ADR.md`, `hybrid_search.py` |
| **Failure modes addressed** | Dense for paraphrase, BM25 for SKUs/policy terms, reranking for ordering, metadata filters for noise | `docs/ADR.md` |
| **Prompt architecture** | Context injection, source ID exposure, missing/low-confidence evidence handling | `docs/ADR.md`, `prompt_builder.py` |
| **What would change with two more weeks** | Larger datasets, production vector infra, stronger NLI verification, deeper monitoring | `docs/ADR.md` |

### 4.3 Evaluation Framework

| Evaluation Requirement | How addressed | Where to look |
|------------------------|---------------|---------------|
| **At least 20 test queries** | Product, policy, customer, and cross-domain questions across easy, medium, and hard difficulty | `test_queries.json` |
| **Multiple domains represented** | Product knowledge, policy operations, customer context, and cross-domain combinations | `test_queries.json` |
| **Recall@K** | Recall@5 against expected chunk IDs for answerable RAG queries | `metrics.py` |
| **MRR** | Mean Reciprocal Rank — measures whether relevant chunks appear early | `metrics.py` |
| **Context Precision** | Measures how much retrieved context is actually relevant | `metrics.py` |
| **Faithfulness** | Judge checks whether answer claims are supported by retrieved evidence | `metrics.py`, `guardrails.py` |
| **Answer Relevance** | Judge checks whether the response directly addresses the user query | `metrics.py` |
| **Hallucination Rate** | Unsupported claims tracked and surfaced in aggregate results | `metrics.py`, `harness.py` |
| **Behavior-aware eval** | Clarification and refusal cases scored as behavior success, not failed retrieval | `harness.py` |
| **Failure analysis** | Identifies worst-performing queries and categorizes retrieval/generation issues | `failure_analysis.py`, `failure_analysis.md` |
| **Regression harness under 5 min** | Smoke mode runs smaller representative subset; full mode runs the full suite | `__main__.py`, `regression.py` |
| **Cost-efficient evaluation** | Smoke/full modes, baseline save/compare, optional output files | `__main__.py` |
| **Tooling explanation** | ADR explains why custom metrics and LLM-as-judge were used instead of framework defaults | `docs/ADR.md` |

### 4.4 Reliability & Production Readiness Memo

| Requirement | How addressed | Where to look |
|-------------|---------------|---------------|
| **Staleness and index drift** | Registry tracks chunk content hashes and tombstones removed content | `registry.py`, `production_readiness_memo.md` |
| **Incremental updates** | Registry identifies new, modified, unchanged, and deleted chunks for incremental refresh | `registry.py`, `run_ingestion.py` |
| **Retrieval failure modes** | Answerability gate detects missing evidence and returns insufficient-context response | `pipeline.py` |
| **Nothing relevant retrieved** | Pipeline checks evidence before generation; can refuse or ask for clarification | `pipeline.py` |
| **Latency budget** | Eval harness reports mean, p50, p95 latency; production memo discusses optimization paths | `harness.py`, `production_readiness_memo.md` |
| **Guardrails** | Faithfulness guardrail verifies answer support and fails closed for high-risk responses | `guardrails.py`, `pipeline.py` |
| **Out-of-scope queries** | Scope guard and deterministic checks prevent unrelated questions from being answered | `scope_guard.py`, `pipeline.py` |
| **Observability** | Pipeline emits trace with intent, chunks, reranking scores, answerability, guardrail status, latency | `models.py`, `pipeline.py` |
| **Demo traceability** | UI exposes trace data so reviewers can inspect how a response was produced | `demo/app/page.tsx`, `server.py` |
| **Top production risks** | Stale content, provider outages, embedding fallback, latency, hallucination, privacy, monitoring | `production_readiness_memo.md` |

### 4.5 Quick Reviewer Navigation

If you only have a few minutes, these are the most useful files to open first:

| Reviewer question | Start here |
|-------------------|------------|
| "How does the RAG pipeline work end-to-end?" | `src/pipeline.py` |
| "Why did you choose this architecture?" | `docs/ADR.md` |
| "How do you retrieve evidence?" | `hybrid_search.py` |
| "How do you prevent unsupported answers?" | `pipeline.py`, `guardrails.py` |
| "How do you evaluate it?" | `harness.py`, `test_queries.json` |
| "How production-ready is this?" | `production_readiness_memo.md` |
| "How do I run it?" | `README.md` |

---

## 5. Effort Investment Distribution

Below is a rough breakdown of how the ~23 hours were spent across the major workstreams. The bars are proportional to time invested.

| Workstream | Description | Time |
|------------|-------------|------|
| **Retrieval Engine** | Hybrid search, RRF fusion, BM25, reranker, metadata filters, fabric/policy boosts | 6.5 h |
| **Ingestion & Chunking** | Domain-aware chunkers, loaders, fabric glossary, document registry, embedders | 4 h |
| **Evaluation Framework** | 28 test queries, retrieval + generation metrics, failure analysis, regression harness | 4 h |
| **Query Intelligence** | Intent router, scope guard, HyDE, query decomposition, answerability gate | 4 h |
| **Generation & Guardrails** | Prompt builder, LLM client, faithfulness guardrail, customer context injection | 2.5 h |
| **Documentation** | ADR, production readiness memo, failure analysis, changelog, README | 1 h |
| **Demo UI** | Next.js chat frontend, assistant-ui integration, trace panel, streaming | ~40 min |
| **Synthetic Data** | Product catalog, policy documents, 25 customer profiles with order histories | ~30 min |
| **Total** | | **~23 hours** |

> **Where the time went**
>
> Retrieval and ingestion together account for roughly 45% of the effort. That's intentional: getting the right evidence to the LLM is the hardest part of a production RAG system. Evaluation and query intelligence each took 4 hours because the assignment weighted evaluation heavily, and because building behavior-aware eval (scoring clarification and refusal as success) required custom metric design. The demo UI took under an hour thanks to assistant-ui doing the heavy lifting.

---

*ALO RAG System — Solution Overview · Built with care for retail AI*
