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

- **unchanged** — content hash matches the previous registry entry
- **modified** — content hash changed; the previous entry is tombstoned and the new chunk version is indexed
- **new** — no prior registry entry exists; the chunk is embedded and inserted

The local POC uses ChromaDB and may run in non-persistent mode during server startup. Because a non-persistent vector collection can be empty even when the registry says a chunk is unchanged, the server now verifies vector availability before skipping unchanged chunks. If the vector store is non-persistent or the vector is missing, the chunk is re-upserted even if the registry hash did not change. This avoids a silent failure mode where BM25 has chunks but dense retrieval has an empty index.

Chunks absent from the incoming source batch are soft-tombstoned immediately. Tombstoned chunks are excluded from active retrieval. A `gc_sweep()` call hard-deletes tombstones older than a configurable retention window.

### Mitigation Strategy

- **Trigger mechanism:** Run the ingestion pipeline on a schedule (cron job, e.g., every 6 hours) or on file-change events from the content management system.
- **Registry/vector consistency:** Validate that vector count, embedding model, embedding dimension, and active registry entries match before serving traffic. If they do not match, rebuild or re-upsert the local index.
- **Validation:** After each ingestion run, use `VectorStore.verify_chunk()` or equivalent round-trip checks to spot-check newly indexed chunks.
- **Monitoring:** Alert if the ingestion pipeline has not run successfully in the last 12 hours, if the tombstone count exceeds a threshold, or if unchanged chunks are being re-upserted frequently during server startup.
- **Rollback:** The registry's tombstone-before-delete pattern means removed content can be recovered within the GC retention window by re-running ingestion with the original source files.

---

## 2. Graceful Degradation

### Risk: External Service Unavailability

The system depends on three major external/runtime components: Voyage AI or the local fallback embedding model, OpenAI for generation/routing/judge calls, and ChromaDB for dense retrieval. Any of these can experience downtime, rate limiting, elevated latency, or local environment issues.

### Mitigation Strategy

| Failure Mode | Impact | Mitigation |
|---|---|---|
| **Voyage AI unavailable or unauthorized** | Cannot compute primary embeddings | `EmbeddingService` automatically falls back to local `sentence-transformers/all-mpnet-base-v2`. Quality may degrade, but the system remains functional. Fallback events are logged and should be included in eval results because they change the actual embedding model used. |
| **OpenAI API unavailable** | Cannot generate answers, classify intent, decompose queries, or verify faithfulness | Pipeline stage errors are caught and logged with stage name and input data. High-risk customer/policy responses fail closed instead of returning unverified claims. |
| **ChromaDB unavailable** | Dense retrieval fails | Hybrid search should degrade to BM25-only retrieval where possible. Results will be lower quality but still functional for keyword-heavy queries. |
| **Zero retrieval results** | No relevant product/policy chunks found | The answerability gate returns an insufficient-context response instead of letting the LLM answer from parametric memory. |
| **Missing customer context** | Customer/order answer cannot be grounded | The answerability gate returns a clarification asking for customer/order context before generation. |
| **Out-of-scope query** | User asks unrelated questions such as weather or sports | Deterministic out-of-scope detection returns a scoped refusal without retrieval or generation. |
| **Faithfulness guardrail fails** | Cannot verify answer claims | The system fails closed for high-risk customer/policy/cross-domain answers. Malformed judge JSON and verification errors no longer default to success. |

### Design Principle

Every pipeline stage should either return verified output, fall back to a clearly degraded but safe path, or fail closed with a scoped explanation. The system should never convert an infrastructure failure into a confident unsupported answer.

---

## 3. Latency Budget

### Risk: Unacceptable Response Times

Users expect fast responses for a conversational interface. The pipeline has multiple sequential stages, some involving external API calls, that can accumulate latency. The latest measured smoke run is substantially slower than an ideal production target, so latency should be treated as an active optimization area rather than a solved problem.

### Current Measured Latency

Latest 8-query smoke evaluation after panel-hardening changes:

| Metric | Value |
|---|---:|
| Mean latency | 8,654 ms |
| p50 latency | 8,953 ms |
| p95 latency | 10,959 ms |

This smoke run includes retrieval, generation, and evaluation-path behavior depending on the selected queries. It is a useful regression signal but not a full production load test.

### Estimated Latency Breakdown (p50 / p95)

| Stage | Expected local POC range | Notes |
|---|---:|---|
| Rule-based fast path classification | < 5 ms | Applies to obvious product, policy, customer, and out-of-scope patterns |
| LLM intent classification (GPT-4.1-nano) | 80–300 ms | Only when rule-based routing is ambiguous |
| Scope/out-of-scope guard | < 5 ms rule-based / 80–300 ms LLM | Deterministic guard handles obvious unrelated queries |
| HyDE generation | 250–800 ms | Only for selected policy queries |
| Query embedding | 50–300 ms | Depends on Voyage vs local fallback model |
| Dense retrieval (ChromaDB) | 20–100 ms | Local vector search |
| Sparse retrieval (BM25) | 5–20 ms | In-memory index |
| RRF fusion and metadata filtering | < 5 ms | Pure computation |
| Policy/fabric companion expansion | < 10 ms | In-memory tag/entity lookup |
| Cross-encoder reranking | 150–600 ms | Local `bge-reranker-base`; CPU/MPS dependent |
| Prompt building | < 5 ms | String assembly |
| LLM generation (GPT-4o) | 3,000–8,000+ ms | Dominant source of latency in recent local runs |
| Faithfulness verification | 0 ms interactive if bypassed / 500–2,000+ ms eval | Full eval uses judge calls; interactive path may use no-op guardrail for speed |

### Mitigation Strategy

- **Conditional stages:** HyDE, query decomposition, and LLM classification should run only when rules are ambiguous or policy vocabulary mismatch is likely.
- **Fast-path routing:** Obvious product/fabric, policy, customer, and out-of-scope queries should avoid unnecessary LLM calls.
- **Answerability short-circuit:** Missing customer context and out-of-scope queries should return immediately without retrieval/generation.
- **Embedding fallback transparency:** Record whether `voyage-3` or `all-mpnet-base-v2` was used because fallback affects both quality and latency.
- **Reranker optimization:** Export the reranker to ONNX or use a smaller/fine-tuned model if p95 latency remains above target.
- **Streaming:** Keep streaming in the demo so users see progress while generation completes.
- **Semantic answer cache:** Cache safe, source-grounded answers for repeated product/policy questions once evidence invalidation is wired to registry changes.
- **Timeout policy:** Set a hard timeout on the full pipeline. If exceeded, return a safe incomplete/try-again response rather than continuing indefinitely.

---

## 4. Observability

### Risk: Silent Failures and Performance Degradation

Without structured logging, metrics, and alerting, issues like embedding fallback, retrieval precision degradation, increased hallucination rates, or latency spikes can go undetected until users report problems.

### Current Implementation

Every pipeline stage appends a timed entry to the `TraceLog` dataclass, capturing:

- Stage name
- Input data (query text, sub-queries, customer_id)
- Output data (classification results, chunk IDs, scores)
- Decision points (HyDE activated, scope guard triggered, answerability action, regeneration triggered)
- Latency in milliseconds
- Retrieved chunks and reranking scores
- Answerability decision where available
- Faithfulness result and evidence-claim records where verification runs

The trace log is accessible via the Demo UI's Trace Mode toggle and as a programmatic return value in `PipelineResult.trace`.

### Production Observability Strategy

**Structured Logging:**
- All log entries should be structured JSON emitted to stdout, suitable for ingestion by CloudWatch, Datadog, or any log aggregator.
- Each log entry should include timestamp, log level, stage name, request ID, customer/session ID when allowed, and relevant context fields.
- Error logs should include the full stage name, input type, and exception details for rapid debugging.

**Key Metrics to Track:**

| Metric | Threshold | Alert Condition |
|---|---|---|
| End-to-end p95 latency | 12,000 ms POC / 3,000 ms production target | p95 above threshold over a 5-minute window |
| Faithfulness score (mean) | 0.8 target | Mean score < 0.7 over a regression window |
| Hallucination rate | < 15% target | Rate > 20% in full eval or online judge sample |
| Context Precision | > 0.45 target | Mean below target in regression run |
| Behavior Success Rate | 100% for explicit clarify/refuse tests | Any expected clarification/refusal test fails |
| Embedding fallback rate | 0% expected in configured production | Any fallback event unless explicitly configured |
| Error rate per stage | 1% | Any stage exceeding 1% error rate over 5 minutes |
| Scope/refusal rate | Baseline-dependent | Sudden spike may indicate routing drift or content outage |
| Ingestion pipeline staleness | 12 hours | No successful ingestion run in 12 hours |
| Registry/vector mismatch | 0 expected | Any mismatch before serving traffic |

**Alerting Tiers:**

- **P1 (page):** OpenAI API errors > 5% for 5 minutes, end-to-end error rate > 5%, customer/policy answerability gate failing open.
- **P2 (ticket):** Embedding fallback activated, p95 latency above POC/production target, faithfulness score drop, registry/vector mismatch.
- **P3 (dashboard):** Regeneration rate trending up, scope guard refusal rate elevated, ingestion staleness approaching threshold, context precision drifting downward.

**Dashboards:**
- **Real-time:** Query volume, latency percentiles, error rates by stage, answerability actions, active fallbacks.
- **Daily:** Faithfulness score distribution, hallucination rate trend, retrieval recall by domain, behavior success rate, top failing queries.
- **Weekly:** Regression comparison against baseline, ingestion delta summary, model cost tracking, failed-query root-cause distribution.

---

## Top Operational Risks — Summary

| # | Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|---|
| 1 | Stale policy content causing incorrect answers | High | Medium | Registry-based refresh, tombstoning, staleness alerting, and policy effective-date/version metadata in production |
| 2 | OpenAI API outage blocking generation and judge calls | High | Low | Graceful error responses, fail-closed high-risk answers, P1 alerting |
| 3 | Embedding provider fallback changing retrieval quality | Medium | Medium | Log fallback events, include embedding model in eval results, validate Voyage API key before final eval |
| 4 | Dense index drift from registry/vector mismatch | High | Medium | Re-upsert unchanged chunks when vector store is non-persistent or missing vectors; validate vector count before serving |
| 5 | Latency spikes from LLM provider | Medium | Medium | Fast-path routing, conditional HyDE/decomposition, streaming, caching, timeout policy |
| 6 | Hallucination on edge-case policy/customer queries | High | Medium | Answerability gate, fail-closed faithfulness guardrail, evidence contracts, behavior-aware eval |
| 7 | Customer data privacy exposure | High | Low | Structured lookup only; customer data never embedded; access controlled by authenticated customer/session context |
| 8 | Safe refusal/clarification being mis-scored as failure | Medium | Medium | Behavior-aware eval with `expected_behavior` and Behavior Success Rate |
| 9 | Conversation history leakage across sessions | Medium | Low | History is scoped to the current HTTP request only — no server-side session state is persisted between requests. Each call to `/api/chat` receives the full message array from the client; no cross-user data is retained. |