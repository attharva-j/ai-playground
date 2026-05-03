# Production Readiness Memo — ALO RAG System

**Date:** 2025-Q1
**Status:** Pre-production assessment
**Author:** ALO RAG Engineering

---

## Purpose

This memo identifies the top operational risks for deploying the ALO RAG system to production and outlines mitigation strategies for each. It covers four areas required for production readiness: incremental index refresh, graceful degradation, latency budget management, and observability.

---

## 1. Incremental Index Refresh

### Risk: Stale Answers from Outdated Index Content

Policy updates (e.g., a changed return window), catalog changes (new products, discontinued SKUs, price adjustments), and customer data updates happen continuously. If the index is not refreshed, the system will serve answers based on outdated information — a compliance and trust risk for policy queries in particular.

### Current Implementation

The `DocumentRegistry` (SQLite-backed) tracks a SHA-256 content hash per chunk. On each ingestion run, every chunk is classified as:

- **unchanged** — skip entirely (no embedding call, no index write)
- **modified** — tombstone the old entry, re-embed, and upsert the new version
- **new** — embed and insert

Chunks absent from the incoming source batch are soft-tombstoned immediately. Tombstoned chunks are filtered at query time so they never appear in results. A `gc_sweep()` call hard-deletes tombstones older than a configurable retention window (default: 24 hours).

### Mitigation Strategy

- **Trigger mechanism:** Run the ingestion pipeline on a schedule (cron job, e.g., every 6 hours) or on file-change events from the content management system. The incremental design means most runs complete in seconds when only a few chunks have changed.
- **Validation:** After each ingestion run, use `VectorStore.verify_chunk()` to spot-check round-trip integrity on a random sample of newly indexed chunks.
- **Monitoring:** Alert if the ingestion pipeline has not run successfully in the last 12 hours, or if the tombstone count exceeds a threshold (indicating large-scale content removal that may warrant manual review).
- **Rollback:** The registry's tombstone-before-delete pattern means removed content can be recovered within the GC retention window by re-running ingestion with the original source files.

---

## 2. Graceful Degradation

### Risk: External Service Unavailability

The system depends on three external services: Voyage AI (embeddings), OpenAI (generation, intent routing, faithfulness verification), and ChromaDB (vector storage). Any of these can experience downtime, rate limiting, or elevated latency.

### Mitigation Strategy

| Failure Mode | Impact | Mitigation |
|---|---|---|
| **Voyage AI unavailable** | Cannot compute new embeddings | `EmbeddingService` automatically falls back to local `all-mpnet-base-v2`. Quality degrades slightly but the system remains functional. Fallback events are logged for monitoring. |
| **OpenAI API unavailable** | Cannot generate answers, classify intent, or verify faithfulness | Pipeline stage errors are caught and logged with stage name and input data. The system returns a safe error response ("I'm sorry, but I encountered an issue…") rather than propagating exceptions. No partial or hallucinated answers are returned. |
| **ChromaDB unavailable** | Dense retrieval fails | Hybrid search can degrade to BM25-only sparse retrieval if dense search throws an exception. Results will be lower quality but still functional for keyword-heavy queries. |
| **Zero retrieval results** | No relevant chunks found | The pipeline detects empty retrieval and generates a scoped refusal ("I don't have enough information to answer that") rather than hallucinating from the LLM's parametric knowledge. |
| **Faithfulness guardrail fails** | Cannot verify answer claims | The original answer is returned as-is. The trace log records that faithfulness verification was skipped, and the `faithfulness_score` is set to `None`. |

### Design Principle

Every pipeline stage is wrapped in a try/except block that logs the error with structured context (stage name, input data, error details) and either falls back to a degraded path or returns a safe error response. The pipeline never halts entirely due to a single stage failure.

---

## 3. Latency Budget

### Risk: Unacceptable Response Times

Users expect sub-2-second responses for a conversational interface. The pipeline has multiple sequential stages, some involving external API calls, that can accumulate latency.

### Estimated Latency Breakdown (p50 / p95)

| Stage | p50 | p95 | Notes |
|---|---|---|---|
| Intent Classification (GPT-4.1-nano) | 80 ms | 250 ms | Lightweight LLM call; GPT-4.1-nano chosen for lower latency on short structured outputs |
| Scope Guard (when triggered) | 80 ms | 250 ms | Only for ambiguous queries; also uses GPT-4.1-nano |
| HyDE Generation (when triggered) | 250 ms | 600 ms | Only for policy queries with confidence > 0.5 |
| HyDE Embedding | 50 ms | 100 ms | Single text embedding |
| Query Decomposition | 150 ms | 400 ms | LLM call; skipped for single-domain queries |
| Dense Retrieval (ChromaDB) | 20 ms | 50 ms | Local vector search, top-12 |
| Sparse Retrieval (BM25) | 5 ms | 15 ms | In-memory index, top-8 |
| RRF Fusion | < 1 ms | < 1 ms | Pure computation |
| Cross-Encoder Reranking | 150 ms | 300 ms | Local model inference on ~20 candidates |
| Prompt Building | < 1 ms | < 1 ms | String assembly |
| LLM Generation (GPT-4o) | 400 ms | 1,000 ms | Primary generation call |
| Faithfulness Guardrail | 0 ms (interactive) / 300 ms (eval) | 0 ms (interactive) / 800 ms (eval) | Bypassed in interactive mode via `_NoOpGuardrail` for latency; full GPT-4o verification runs in eval harness only |
| **Total (simple query, interactive)** | **~375 ms** | **~950 ms** | Product query, no HyDE, no decomposition, guardrail bypassed |
| **Total (complex query, interactive)** | **~700 ms** | **~1,700 ms** | Policy + HyDE + decomposition, guardrail bypassed; HyDE and decomposition run in parallel |
| **Total (complex query, eval harness)** | **~1,200 ms** | **~2,800 ms** | Same as above but with full faithfulness verification |

**Note:** Intent classification uses rule-based fast paths for common query patterns, falling back to GPT-4.1-nano only when rules are ambiguous. Fast-path queries skip the LLM call entirely, reducing intent classification to < 1 ms.

### Mitigation Strategy

- **Parallel retrieval:** Dense and sparse searches execute in parallel threads, saving ~20 ms on the critical path.
- **Conditional stages:** HyDE, scope guard, and query decomposition only activate when their trigger conditions are met, keeping simple queries fast.
- **Model selection:** Intent classification, scope guard, HyDE generation, and query decomposition use GPT-4.1-nano (faster and cheaper than GPT-4o for short structured outputs). Only the primary answer generation uses GPT-4o. The faithfulness guardrail uses GPT-4o in the eval harness but is bypassed entirely in interactive mode via a no-op implementation, eliminating its ~300–800 ms cost from the interactive critical path without compromising offline quality measurement.
- **Parallel execution:** HyDE and query decomposition run concurrently in `ThreadPoolExecutor` — on multi-domain policy queries this eliminates ~350 ms of sequential wait since neither stage depends on the other's output.
- **Embedding caching:** For repeated or similar queries, cache query embeddings to avoid redundant Voyage API calls. A simple LRU cache with TTL covers the common case.
- **Reranker optimization:** The cross-encoder processes only the fused candidate set (~15–20 chunks), not the full index. Batch inference keeps this under 300 ms at p95.
- **Conversation history token budget:** Multi-turn context (last 6 messages, up to 3 exchanges) is injected into the generation prompt. Long assistant turns are truncated to 300 characters before injection. This bounds the additional token cost to approximately 400–600 tokens per request in the worst case, well within GPT-4o's context window and not on the critical latency path.
- **Timeout policy:** Set a 5-second hard timeout on the full pipeline. If exceeded, return whatever partial result is available with a note that the response may be incomplete.

---

## 4. Observability

### Risk: Silent Failures and Performance Degradation

Without structured logging, metrics, and alerting, issues like embedding quality degradation, increased hallucination rates, or latency spikes can go undetected until users report problems.

### Current Implementation

Every pipeline stage appends a timed entry to the `TraceLog` dataclass, capturing:

- Stage name
- Input data (query text, sub-queries, customer_id)
- Output data (classification results, chunk IDs, scores)
- Decision points (HyDE activated, scope guard triggered, regeneration triggered)
- Latency in milliseconds

The trace log is accessible via the Demo UI's Trace Mode toggle and as a programmatic return value in `PipelineResult.trace`.

### Production Observability Strategy

**Structured Logging:**
- All log entries are structured JSON emitted to stdout, suitable for ingestion by CloudWatch, Datadog, or any log aggregator.
- Each log entry includes: timestamp, log level, stage name, and relevant context fields.
- Error logs include the full stage name, input data, and exception details for rapid debugging.

**Key Metrics to Track:**

| Metric | Threshold | Alert Condition |
|---|---|---|
| End-to-end p95 latency | 3,000 ms | p95 > 3,000 ms over a 5-minute window |
| Faithfulness score (mean) | 0.7 | Mean score < 0.7 over a 5-minute window |
| Embedding fallback rate | 0% | Any fallback event (indicates Voyage API issue) |
| Error rate per stage | 1% | Any stage exceeding 1% error rate over 5 minutes |
| Scope guard refusal rate | 10% | Refusal rate > 10% (may indicate intent router drift) |
| Regeneration trigger rate | 20% | Regeneration rate > 20% (may indicate prompt or retrieval degradation) |
| Ingestion pipeline staleness | 12 hours | No successful ingestion run in 12 hours |

**Alerting Tiers:**

- **P1 (page):** OpenAI API errors > 5% for 5 minutes, end-to-end error rate > 5%.
- **P2 (ticket):** Embedding fallback activated, p95 latency > 3s for 15 minutes, faithfulness score drop.
- **P3 (dashboard):** Regeneration rate trending up, scope guard refusal rate elevated, ingestion staleness approaching threshold.

**Dashboards:**
- **Real-time:** Query volume, latency percentiles, error rates by stage, active fallbacks.
- **Daily:** Faithfulness score distribution, hallucination rate trend, retrieval recall by domain, top failing queries.
- **Weekly:** Regression comparison against baseline, ingestion delta summary, model cost tracking.

---

## Top Operational Risks — Summary

| # | Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|---|
| 1 | Stale policy content causing incorrect answers | High | Medium | Incremental refresh via DocumentRegistry on a 6-hour schedule; staleness alerting |
| 2 | OpenAI API outage blocking all generation | High | Low | Graceful error responses; no hallucinated partial answers; P1 alerting |
| 3 | Embedding model degradation (silent quality drop) | Medium | Low | Evaluation regression harness run weekly; faithfulness score monitoring |
| 4 | Latency spikes from LLM provider | Medium | Medium | Conditional stage activation; GPT-4.1-nano for lightweight calls; faithfulness guardrail bypassed in interactive mode; 5s hard timeout |
| 5 | Hallucination on edge-case queries | Medium | Medium | Faithfulness guardrail with regeneration; scope guard for out-of-scope refusal; evaluation suite with intentional trap queries |
| 6 | Customer data privacy exposure | High | Low | Structured lookup (not embedded); customer data never enters the vector store; access controlled by customer_id from authenticated session |
| 7 | Conversation history leakage across sessions | Medium | Low | History is scoped to the current HTTP request only — no server-side session state is persisted between requests. Each call to `/api/chat` receives the full message array from the client; no cross-user data is retained. |