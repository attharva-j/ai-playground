# Architecture Decision Record — ALO RAG System

**Date:** 2025-Q1
**Status:** Accepted
**Author:** ALO RAG Engineering

---

## Decision Summary

Skim through the overview for a quick understanding of architecture decisions; keep reading for detailed reasoning for each individual decision.

### Overview

| # | Decision area | Chosen | One-line reason | Future path |
|---|---|---|---|---|
| ADR-1 | Chunking | Per-domain: one chunk per product + fabric entity chunks; section-based policy chunks with tags | Each domain has different boundary rules; fabric comparison and policy edge cases need entity/section-level evidence | Sliding-window chunking for large catalog scale; parent-child section expansion if policy corpus grows significantly |
| ADR-2 | Embedding model | **voyage-3** (primary) + all-mpnet-base-v2 (auto-fallback) | voyage-3 leads MTEB benchmarks on retail/policy text; fallback prevents hard dependency on a single API | Domain fine-tuned embeddings for production; evaluate Cohere embed-v3 if vendor consolidation matters |
| ADR-3 | Retrieval | Hybrid dense + sparse BM25, fused via **RRF (k=60)**, with hard domain filters, fabric boosts, and policy companion chunks | Dense misses rare vocabulary; BM25 misses abstract paraphrase; entity/tag-aware retrieval improves precision for retail terms and multi-clause policy questions | SPLADE learned sparse retrieval; managed vector DB (Pinecone/Weaviate/OpenSearch) at scale |
| ADR-3b | HyDE | Activated **only for policy queries** (confidence > 0.5), using GPT-4.1-nano | Policy queries have the widest vocabulary gap between casual language and formal document text; other domains don't benefit enough to justify the added LLM call | Query rewriting before retrieval for multi-turn conversations (rewrites follow-up queries into standalone queries) |
| ADR-4 | Customer data | **Structured JSON lookup** by `customer_id`; never embedded; answerability gate for missing customer context | Return eligibility needs exact booleans and date arithmetic; embedding PII creates privacy risk; missing customer data must trigger clarification, not generation | PostgreSQL / DynamoDB for production; row-level security and authenticated session binding at the storage layer |
| ADR-5 | Prompt architecture | Numbered chunks with ID + relevance score; optional customer section; answerability/evidence-contract trace; last 3 conversation turns injected | Chunk IDs enable source citation and guardrail verification; answerability prevents unsupported answers; evidence contracts expose claim support | Query-aware history rewriting before retrieval; dynamic `final_k` tuned per domain from eval data |
| ADR-6 | Reranker model | **BAAI/bge-reranker-base** + `min_score = -3.0` floor | MiniLM-L6 (MS MARCO trained) scored 0.208 Context Precision; bge-reranker-base is trained on diverse corpora including domain-specific text; same interface, free, local | bge-reranker-v2-m3 on GPU (~150ms); ONNX export for 5× CPU speedup; fine-tuned model on ALO pairs long-term |
| ADR-7 | Eval tooling | **Custom LLM-as-judge** prompts + deterministic retrieval metrics + behavior-aware safety metrics; RAGAS + DeepEval installed but not active | Full control over scoring rubric; behavior tests score clarify/refuse actions separately from answerable QA; uses existing LLM client | Integrate RAGAS/DeepEval adapters at stable release; NLI model replacing LLM-as-judge for faithfulness; LangSmith for team dashboards |

---

### Rejected alternatives — by decision

#### ADR-1 — Chunking

| Alternative | Rejected because |
|---|---|
| Fixed 512-token chunks with overlap | Content-unaware; splits conditional policy clauses across chunk boundaries, breaking retrieval on the most important query types |
| Recursive character splitter | Better boundary detection than fixed-size, but still content-unaware; cannot guarantee if/then/else blocks stay intact |

#### ADR-2 — Embedding model

| Alternative | Rejected because |
|---|---|
| OpenAI text-embedding-3-large | Higher per-token cost; no benchmark advantage over voyage-3 on retail/policy domains |
| all-mpnet-base-v2 as primary | Lower quality on nuanced policy language; kept as auto-fallback for resilience, not as primary |
| Cohere embed-v3 | Introduces a third vendor relationship for marginal quality gain |

#### ADR-3 — Retrieval approach

| Alternative | Rejected because |
|---|---|
| Dense-only retrieval | Fails on exact-term queries (SKU codes, "Aloversary Sale") where the embedding model has sparse training signal |
| Sparse-only (BM25) | Fails on abstract paraphrase — "can I get my money back if something doesn't fit?" has no keyword overlap with the answer |
| Linear score combination | Requires tuning a per-domain weight α; breaks when one modality returns zero results; BM25 and cosine scores are incompatible in scale |
| All candidates directly to cross-encoder (no fusion) | Slower — the reranker must score the full unfiltered union; RRF pre-filters to a higher-quality candidate pool |

#### ADR-3b — HyDE

| Alternative | Rejected because |
|---|---|
| HyDE for all domains | Adds a ~300ms LLM call to every query; product queries rarely suffer vocabulary mismatch; customer queries use structured lookup |
| No HyDE | Policy retrieval recall drops measurably on abstract questions, which are the highest-value policy query type |
| Query expansion (synonym injection) | Less effective than HyDE; cannot generate the specific conditional phrasing ("eligible", "30-day window", "Final Sale") that policy chunks contain |

#### ADR-4 — Customer data architecture

| Alternative | Rejected because |
|---|---|
| Embed order history as chunks | Arithmetic and boolean logic fail under similarity search; PII in a shared vector store creates cross-customer privacy risk; order statuses change continuously and re-embedding is expensive |
| Hybrid (embed summaries, look up details) | Adds complexity with no benefit — the intent router already identifies customer queries and `customer_id` is provided by the UI |

#### ADR-5 — Prompt architecture

| Alternative | Rejected because |
|---|---|
| Flat context dump with no chunk IDs | Claims cannot be traced to sources; faithfulness guardrail has no audit trail to verify against |
| Summarising chunks before injection | Lossy transformation; summarisation can introduce its own errors and adds latency before every generation call |

#### ADR-6 — Reranker model

| Alternative | Rejected because |
|---|---|
| ms-marco-MiniLM-L-12-v2 | Same MS MARCO training data as L-6; vocabulary mismatch problem remains; 50% slower for no quality gain in this domain |
| BAAI/bge-reranker-v2-m3 | 568M parameters; 2.5× slower than bge-reranker-base on CPU; needs GPU to be practical — **recommended when GPU is available** |
| Cohere Rerank 3.5 | API round-trip adds ~900ms; per-query cost; external dependency — **appropriate for production if budget allows** |
| Voyage AI rerank-2 | Same API-latency and cost concerns as Cohere; natural pairing with voyage-3 but not justified at POC scale |
| Fine-tuning on ALO pairs | Requires 200+ labelled (query, chunk, hard-negative) triplets that do not yet exist — **the long-term highest-quality path** |

#### ADR-7 — Evaluation tooling

| Alternative | Rejected because |
|---|---|
| RAGAS (active) | Requires reformatting `PipelineResult` into RAGAS `Dataset` schema; scoring prompts are not inspectable without reading library source; introduces a second LLM client configuration — **recommended for stable release** |
| DeepEval (active) | Primary value is CI/CD integration (pass/fail assertions, dashboards) — not relevant at POC scale; forces `EvaluationTestCase` wrapper with no added capability — **recommended for production** |
| LangSmith | Observability and tracing platform, not a metrics library; duplicates the existing `TraceLog` implementation — **recommended for production team dashboards** |
| TruLens | Designed for LangChain/LlamaIndex pipelines; requires instrumentation wrappers incompatible with this custom pipeline architecture |

#### Deferred improvements *(not rejected — deferred)*

| Item | Why deferred | When to build |
|---|---|---|
| Semantic query cache | Out of scope for POC; no repeated-query traffic to measure benefit against | Before production launch |
| Self-evaluating retrieval loop | Requires defining a per-domain confidence threshold; needs eval data to calibrate | After eval suite is stable |
| NLI model for faithfulness | Requires downloading and validating a local model in the target environment | Next iteration; cuts guardrail latency from ~800ms to ~200ms |
| ONNX reranker export | One-time manual export step requiring the target environment to be available | When deployment environment is confirmed |
| Query-aware retrieval history | Requires an additional LLM call per multi-turn query; needs multi-turn eval queries to measure benefit | Stable release |
| 50+ customer profiles with adversarial/long-tail edge cases | The panel-hardening pass expanded the synthetic dataset target to 25 profiles; a larger set would support better distributional coverage | Before production pilot |
---

## ADR-1: Per-Domain Chunking Strategy

### Context

The ALO RAG system ingests three distinct knowledge domains — product catalog (structured JSON), policy documents (long-form Markdown with conditional logic), and customer order data (structured JSON). Each domain has fundamentally different information density, query patterns, and retrieval requirements. A single chunking strategy cannot serve all three well.

### Decision

Use domain-specific chunking strategies:

- **Products:** One chunk per product, concatenating all fields (name, description, materials, sizing, care instructions, features) into a single text block with metadata tags for `product_id`, `category`, `fabric_type`, and `entity_type="product"`.
- **Fabric entities:** First-class fabric glossary chunks such as `fabric-airlift` and `fabric-airbrush` are generated alongside product chunks. These chunks contain comparison-ready fabric attributes and are tagged with `entity_type="fabric"` and `fabric_name` so fabric comparison queries retrieve fabric-level evidence instead of relying on incidental SKU-level text.
- **Policies:** Semantic section-based chunking that splits at heading boundaries and topic shifts, preserving complete conditional logic blocks (if/then/else rules) within a single chunk. Metadata includes `policy_type`, `effective_date`, `policy_tags`, `entity_type="policy_section"`, `parent_id`, and `section_id`.
- **Customers:** No chunking — customer data is handled via structured lookup (see ADR-4).

### Alternatives Considered

1. **Fixed 512-token chunks with overlap:** Simple to implement and framework-agnostic. However, it risks splitting a product's care instructions from its fabric description, or breaking a conditional return-eligibility rule across two chunks. Both degrade retrieval quality for the most common query types.
2. **Recursive character splitter (LangChain-style):** Slightly better boundary detection than fixed-size, but still content-unaware. It cannot guarantee that an if/then/else block in a policy document stays intact.

### Rationale

Product queries often need the full product context ("What fabric is the Airlift Legging made of?" requires fabric, materials, and care instructions together). One-chunk-per-product guarantees a single retrieval hit returns product-level evidence. However, comparison questions such as "Airlift vs Airbrush" are better answered from fabric-level entities than from arbitrary product SKUs, so the system now creates fabric glossary chunks with deterministic IDs and metadata. Policy queries frequently target conditional rules ("Can I return a Final Sale item?"), and splitting those rules across chunks would force the retriever to find and reassemble both halves — a fragile pattern. Policy tags and parent/section IDs make those related clauses easier to retrieve and trace.

---

## ADR-2: Embedding Model Selection — Voyage AI voyage-3

### Context

Dense retrieval quality depends heavily on embedding model choice. The system needs high-quality semantic embeddings for both product descriptions and policy text, with reasonable cost and latency for a proof-of-concept that may scale to production.

### Decision

Use **Voyage AI voyage-3** as the primary embedding model, with **sentence-transformers/all-mpnet-base-v2** as an automatic fallback when the Voyage API is unavailable.

### Alternatives Considered

1. **OpenAI text-embedding-3-large:** Strong general-purpose embeddings, but higher per-token cost and no clear advantage over voyage-3 on retail/policy domain benchmarks. Would consolidate on a single API provider (OpenAI) but at higher embedding cost.
2. **all-mpnet-base-v2 as primary:** Free, runs locally, no API dependency. However, embedding quality is measurably lower on semantic similarity benchmarks, particularly for nuanced policy language where vocabulary gaps matter most. Kept as fallback for resilience.
3. **Cohere embed-v3:** Competitive quality, but introduces yet another API key and vendor relationship for marginal gain.

### Rationale

voyage-3 offers strong retrieval quality on MTEB benchmarks, competitive pricing, and a clean API. Using it as primary with a local fallback gives the system resilience: if the Voyage API is down or rate-limited, the `EmbeddingService` transparently switches to all-mpnet-base-v2 and logs the fallback event. This avoids a hard dependency on any single external service while keeping embedding quality high for the default path.

**Dimension consistency guarantee:** Once the fallback model is activated during a process lifetime, all subsequent embedding calls use the fallback exclusively — even if the primary model becomes available again. This prevents dimension mismatches between indexing (768-dim fallback) and querying (1024-dim primary) that would cause ChromaDB to reject queries.

---

## ADR-3: Hybrid Retrieval and Reciprocal Rank Fusion (RRF)

### Context

The system must retrieve relevant chunks from two structurally different knowledge domains — product catalog text and policy documents — in response to natural language queries that range from exact-term lookups ("what fabric is the Airlift Legging?") to abstract policy questions ("can I return a sale item?"). A single retrieval strategy cannot handle both ends of this spectrum well.

Dense vector retrieval (embedding cosine similarity) excels at semantic matching but struggles with rare, out-of-distribution vocabulary. If a user asks about "Aloversary Sale" or "Final Sale exclusions", the embedding model may have seen these terms rarely during training and produces embeddings that do not cluster tightly with the correct policy sections. Conversely, keyword search (BM25) excels at exact-term matching but has no understanding of paraphrase — "return window" and "30-day eligibility period" are the same concept to a human but produce zero keyword overlap.

Two retrieval results lists must also be merged into a single ranked list before reranking. The naive approach — normalising and adding cosine similarity and BM25 scores — is fragile because the two score distributions are incompatible: BM25 scores are unbounded and depend on corpus statistics, while cosine similarity is bounded to [-1, 1].

### Decision

Use **hybrid retrieval** combining dense vector search (ChromaDB + voyage-3, top-12 candidates) and sparse BM25 keyword search (rank-bm25, top-8 candidates), merged using **Reciprocal Rank Fusion (RRF)** with the standard smoothing constant k=60.

The RRF formula assigns each chunk a score based solely on its rank in each result list:

```
RRF_score(chunk) = Σ  1 / (rank_i(chunk) + k)
                  i
```

Where `rank_i` is the 1-based position of the chunk in result list `i`, and `k=60` prevents the highest-ranked chunks from dominating when the list is short. A chunk appearing in both lists receives the sum of both contributions — it is promoted relative to chunks appearing in only one list.

The merged list is passed to the cross-encoder reranker, which scores the top candidates jointly and applies a minimum score threshold before returning the final `final_k` chunks.

Recent hardening added three domain-specific retrieval controls:

- **Hard metadata filtering** for clear single-domain queries so product-only queries do not pass policy chunks to reranking, and policy-only queries do not pass product chunks unless the query is cross-domain.
- **Fabric/entity boosting** for known fabric terms such as Airlift and Airbrush so comparison queries retrieve `entity_type="fabric"` chunks.
- **Policy tag companion expansion** for multi-clause policy questions such as military/community discount during a sale event or exchange/return-window questions.

### Alternatives Considered

1. **Dense-only retrieval:** Simpler pipeline, no BM25 index to maintain. Fails on exact-term queries — a user asking about "W5561R-BLK" (an SKU code) or "Aloversary Sale" may get poor results if the embedding model does not recognise the term. Rejected because the product domain has many exact identifiers (SKUs, fabric brand names) that BM25 handles reliably.

2. **Sparse-only retrieval (BM25):** No embedding cost, deterministic results. Fails on paraphrase and abstract policy questions — "can I get my money back if something doesn't fit?" has no keyword overlap with the policy section that answers it. Rejected as the primary strategy but retained as a parallel signal.

3. **Linear score combination (weighted sum):** Normalise BM25 and cosine similarity scores to [0, 1] and add them with weights α and (1-α). Requires tuning α per domain, is sensitive to score distribution shifts when the corpus changes, and breaks when one modality returns zero results (causing the other to dominate by default). Rejected in favour of RRF, which is rank-based and therefore immune to scale differences between modalities.

4. **Single-stage reranking without fusion (all candidates to cross-encoder):** Retrieve the union of dense and sparse results and feed all of them to the cross-encoder without prior fusion. This works but is slower — the cross-encoder must score more pairs. RRF pre-filters by selecting candidates that ranked well in at least one modality, giving the reranker a higher-quality candidate pool to work with.

### Why k=60

The value k=60 comes from the original RRF paper (Cormack, Clarke, and Buettcher, 2009) where it was empirically determined to produce stable fusion results across a range of list lengths. It controls how steeply the score drops off with rank — lower k gives more weight to top-ranked results, higher k distributes weight more evenly. At k=60 with lists of 8–12 items, the score difference between rank 1 and rank 8 is modest (~0.017 vs 0.015), which is intentional: RRF's value is in combining signals, not in amplifying the top-ranked item from either list.

### Failure modes addressed vs. naive top-k

| Failure mode | Naive top-k | Hybrid + RRF |
|---|---|---|
| Rare vocabulary (SKU codes, brand names) | ✗ Dense may miss exact terms | ✓ BM25 recovers via keyword match |
| Abstract paraphrase (different wording, same meaning) | ✗ BM25 misses non-overlapping phrasing | ✓ Dense recovers via semantic similarity |
| Chunk appears in both result lists (strong signal) | ✗ Not modelled | ✓ RRF score accumulates from both contributions |
| Scale incompatibility between BM25 and cosine scores | ✗ Linear combination breaks | ✓ RRF is rank-based; scale-independent |
| Vocabulary mismatch for policy queries | ✓ Partially addressed by HyDE | ✓ BM25 provides a parallel exact-match path |

### Rationale

Hybrid retrieval is the industry-standard approach for production RAG systems precisely because no single retrieval modality dominates across all query types. The combination is robust: when dense retrieval fails (rare vocabulary), BM25 compensates; when BM25 fails (abstract paraphrase), dense retrieval compensates. RRF is the right fusion mechanism for this use case because it requires no tuning, is insensitive to score distribution shifts, and has a principled theoretical basis from the information retrieval literature.

---

## ADR-3b: HyDE for Policy Queries Only

### Context

Policy questions are often abstract and use different vocabulary than the policy documents themselves. A user asking "Can I return sale items?" may not match well against a document section titled "Final Sale Exclusions" that uses terms like "discount threshold" and "ineligible categories." This vocabulary gap reduces dense retrieval recall for policy queries even with hybrid search in place — BM25 helps with known terms, but abstract questions have no keyword overlap with formal policy language.

### Decision

Activate Hypothetical Document Embeddings (HyDE) selectively — only when the intent router classifies a query as `domain="policy"` with confidence above 0.5. When activated, the system generates a hypothetical answer via GPT-4o-mini (the classification model path), embeds that answer, and uses the hypothetical embedding for dense retrieval instead of the raw query embedding. GPT-4o-mini is used rather than GPT-4o because the hypothetical is evaluated only by its embedding proximity to real policy chunks — vocabulary richness matters, not reasoning depth.

### Alternatives Considered

1. **HyDE for all domains:** Adds an LLM call (~300 ms) to every query. Product queries rarely suffer from vocabulary mismatch (users name products directly), and customer queries use structured lookup. The latency cost is not justified for these domains.
2. **No HyDE at all:** Simpler pipeline, lower latency. But policy retrieval recall drops measurably for abstract questions, which are the most common and highest-value policy query type.
3. **Query expansion (synonym injection) instead of HyDE:** Lighter-weight, but less effective at bridging the gap between conversational language and formal policy terminology. HyDE generates a full hypothetical answer that naturally contains the policy vocabulary.

### Rationale

HyDE is most valuable where the vocabulary gap between query and document is largest — policy questions. By gating activation on the intent router's confidence score, the system avoids the latency penalty for product and customer queries where HyDE adds no value. The hypothetical document is recorded in the trace log for full observability, making it easy to debug retrieval issues during evaluation.

---

## ADR-4: Customer Data Architecture — Structured Lookup vs. Embedding

### Context

Customer order data includes personally identifiable information (names, emails), precise numerical values (prices, quantities, dates), and boolean flags (final_sale, was_discounted) that drive business logic. The system needs to answer questions like "Can I return the leggings I bought during Cyber Monday?" which requires exact-match lookup of a specific customer's order items and their `final_sale` status.

### Decision

Handle customer data via **structured JSON lookup** by `customer_id`, not via embedding similarity search. The `CustomerContextInjector` loads customer profiles from JSON and retrieves them by exact ID match. Customer data is injected directly into the generation prompt alongside retrieved policy/product chunks only when a customer-specific query has valid customer context.

A pre-generation **answerability gate** now checks whether required evidence is available before generation. Customer/order-status questions without a customer profile are short-circuited into a clarification response rather than being answered from generic product or policy context.

### Alternatives Considered

1. **Embed order history as chunks:** Each order or order item becomes a chunk in the vector store. This approach fails for several reasons:
   - **Arithmetic imprecision:** Embedding-based retrieval cannot reliably answer "How much did I spend?" — it retrieves semantically similar text, not exact values.
   - **PII surface area:** Embedding customer names and emails into a shared vector store creates unnecessary privacy risk. Any query could potentially surface another customer's data through similarity matching.
   - **Staleness:** Order statuses change (shipped → delivered, return requested → refunded). Re-embedding on every status change is wasteful; structured lookup always returns current state.
   - **Boolean logic:** Determining return eligibility requires checking `final_sale == true` — a boolean comparison, not a semantic similarity operation.

2. **Hybrid approach (embed summaries, lookup details):** Embed a natural-language summary of each customer's history for retrieval, then look up details. Adds complexity without clear benefit since the intent router already identifies customer queries and the customer_id is provided by the UI.

### Rationale

Customer queries are fundamentally different from product and policy queries. They require precise, structured data — exact order dates, boolean flags, numerical totals — not semantic similarity. Structured lookup is faster, more accurate, privacy-safe, and always returns current state. The `customer_id` is provided by the demo UI's dropdown, so there is no need for fuzzy matching or retrieval-based customer identification. The answerability gate is intentionally conservative: if customer evidence is required and not available, the system asks for the customer profile/order context instead of producing a plausible but unsupported answer.


---

## ADR-5: Prompt Architecture

### Context

The system needs a clear strategy for how retrieved context is injected into the LLM prompt and how low-relevance or excessive context is handled.

### Decision

Structured prompt with three sections — Retrieved Context, Customer Context (optional), User Query — assembled by `PromptBuilder`.

### How context is injected

- Each retrieved chunk is numbered and prefixed with its chunk ID in brackets, relevance score, source type, and domain metadata
- This format allows the LLM to cite specific chunks and allows a human reviewer to trace every claim back to its source
- The system message instructs the model to cite chunk IDs for every factual claim using square bracket notation, e.g. `[ALO-LEG-001]`

### How low-relevance context is handled

- The cross-encoder reranker acts as the primary filter — it scores every (query, chunk) pair jointly and discards candidates below the relevance threshold before they reach the prompt
- `final_k` caps the number of chunks injected into the prompt (3 for single-domain queries, 4 per sub-query for multi-domain queries)
- Relevance scores are visible in the prompt so the model can weight uncertain context appropriately rather than treating all chunks as equally authoritative

### System / user message split

- System message: invariant instructions — citation rules, scope constraints, honesty requirements, formatting guidance, and customer-priority instructions (when customer data is present, the model must lead with customer-specific details rather than generic policy)
- User message: query-specific content — conversation history (last 3 exchanges, if any), retrieved chunks with scores, customer context (if applicable), the user's question

### Conversation history injection

For multi-turn conversations, the last 6 messages (3 user-assistant exchanges) are prepended to the user message as a "Conversation History" section. This allows the LLM to resolve pronouns and references across turns ("it", "that order", "what about sale items?") without requiring changes to the retrieval pipeline. Retrieval still targets only the latest user message — prior turns provide generation context, not retrieval signal.

### Context overflow handling

- At POC scale with a small catalog this is not triggered
- Production mitigation: if total chunk text exceeds approximately 6,000 tokens, lower-scoring chunks are dropped from the bottom of the ranked list before prompt assembly

### Answerability and evidence contract

Before prompt construction, the pipeline computes an `AnswerabilityDecision` containing required evidence, available evidence, missing evidence, confidence, reason, and action. The generation layer is skipped when the action is `clarify`, `refuse_insufficient_context`, or `refuse_out_of_scope`. This prevents the model from answering customer/order questions without customer context or policy questions without relevant policy evidence.

The pipeline also records `EvidenceClaim` entries for generated claims when faithfulness verification runs. Each evidence claim maps a natural-language claim to an evidence type (`product`, `policy`, `customer`, or `none`), a source ID when available, support status, and risk level. This is primarily an auditability mechanism for the trace panel and failure analysis; it is not used as a replacement for deterministic retrieval metrics.

### Alternatives considered

1. Flat context dump with no chunk IDs — rejected because the model cannot cite sources and hallucination is harder to detect
2. Summarising chunks before injection — rejected because summarisation is a lossy transformation that can itself introduce errors and adds latency

### Rationale

The structured prompt with explicit chunk IDs and scores gives the LLM the information it needs to produce well-sourced answers while giving the faithfulness guardrail a clear audit trail for verification.

---

## ADR-6: Cross-Encoder Reranker Model Selection

### Context

The retrieval pipeline uses a cross-encoder reranker as the final stage before generation. The cross-encoder reads each (query, candidate chunk) pair jointly and produces a relevance score, giving it substantially higher precision than the embedding cosine similarity used for initial retrieval. The quality of this model directly determines Context Precision — how many of the chunks actually passed to the LLM are relevant to the query.

The initial implementation used `cross-encoder/ms-marco-MiniLM-L-6-v2`, the smallest and most commonly referenced cross-encoder in open-source RAG tutorials. Evaluation results showed a Mean Context Precision of 0.208, meaning roughly 4 in 5 chunks passed to the generation layer were irrelevant. This indicated the reranker was not effectively discriminating relevant from irrelevant chunks in this domain.

### Root Cause of Poor Performance with MiniLM-L6

`ms-marco-MiniLM-L-6-v2` was trained exclusively on the MS MARCO dataset, which consists of real Bing web search queries matched against web document passages. This creates two problems for the ALO RAG use case:

**Vocabulary mismatch:** The model has never encountered retail-specific terminology such as "Aloversary Sale", "Final Sale exclusions", "A-List tier", "Airlift fabric", or "community discount stacking rules". It therefore cannot learn the relevance signal between a query like "Can I use my military discount during the Aloversary Sale?" and the corresponding policy section — the vocabulary is simply out of distribution.

**Query type mismatch:** MS MARCO web search queries are short, keyword-oriented, and typically answered by a single web page passage. ALO policy queries are conversational, require conditional reasoning ("if the item was discounted ≥30% then it is Final Sale"), and often require two policy sections to be retrieved together. The cross-encoder has no learned signal for this kind of query structure.

### Decision

Replace `cross-encoder/ms-marco-MiniLM-L-6-v2` with `BAAI/bge-reranker-base` as the default cross-encoder reranker.

Additionally, add a `min_score` parameter to `CrossEncoderReranker.rerank()` (default: `-3.0`) so that chunks scoring below a configurable threshold are excluded from the output entirely, rather than always returning exactly `top_k` chunks regardless of their relevance scores.

### Why bge-reranker-base

`bge-reranker-base` is developed by the Beijing Academy of Artificial Intelligence (BAAI) and trained on a significantly more diverse corpus than MS MARCO, including academic, legal, and domain-specific passage pairs. Key advantages:

- **Broader training distribution:** Generalises to out-of-domain vocabulary better than MS MARCO-only models
- **Same interface:** Loaded via `sentence-transformers.CrossEncoder`, drop-in replacement
- **Free and local:** No API dependency, no per-query cost
- **Proven on BEIR benchmarks:** Outperforms `ms-marco-MiniLM-L-6-v2` on the majority of BEIR retrieval benchmark domains, particularly on domain-specific corpora

### Alternatives Considered

1. **`cross-encoder/ms-marco-MiniLM-L-12-v2`:** Still trained exclusively on MS MARCO. Vocabulary mismatch remains. Rejected.
2. **`BAAI/bge-reranker-v2-m3`:** Current SOTA open-source cross-encoder, but 568M parameters vs 278M — approximately 2.5× slower. Recommended upgrade path for production with GPU.
3. **Cohere Rerank 3.5:** Highest accuracy, but adds API round-trip (~900ms) and per-query cost. Appropriate for production if budget allows.
4. **Voyage AI rerank-2:** Natural pairing with voyage-3 embeddings. Same API-latency and cost concerns as Cohere.
5. **Fine-tuning on ALO-specific pairs:** Theoretically best, but requires a labelled dataset of 200+ triplets that does not yet exist. Recommended long-term path.

### Latency Impact

| Model | Parameters | Warm CPU latency (15 pairs) |
|---|---|---|
| ms-marco-MiniLM-L-6-v2 (previous) | 22M | ~180ms |
| bge-reranker-base (new) | 278M | ~400ms |
| bge-reranker-v2-m3 (future) | 568M | ~600ms |

The additional ~220ms is acceptable given that GPT-4o generation dominates latency at ~6,900ms, and the streaming architecture means retrieval latency completes before the first token is shown. See ADR-3 for the full hybrid retrieval and RRF design that this reranker operates within.

### Rationale

The quality improvement in Context Precision is expected to reduce hallucination rate, which is a higher-priority concern than 220ms of additional retrieval time. This is the pragmatic short-term improvement pending a fine-tuned model trained on ALO-specific query/chunk pairs.

---

## ADR-7: Evaluation Tooling — LLM-as-Judge vs. Framework Libraries

### Context

The brief permits any combination of RAGAS, TruLens, DeepEval, LangSmith, and LLM-as-judge prompts for evaluation, with a requirement to explain the choice. The evaluation framework must compute at least two retrieval metrics and two generation metrics, identify the three worst-performing queries, and support a regression test harness runnable in under five minutes.

Three categories of tooling were available:

- **Framework libraries** (RAGAS, DeepEval, TruLens): pre-built metric pipelines with opinionated scoring implementations, managed evaluation datasets, and in some cases cloud dashboards.
- **Observability platforms** (LangSmith): tracing and logging infrastructure for LLM pipelines, with eval capabilities layered on top.
- **LLM-as-judge prompts**: custom prompts sent to an LLM that score outputs against defined criteria, with full control over the scoring rubric, model selection, and output format.

### Decision

Implement generation metrics using **custom LLM-as-judge prompts** via the existing `LLMClient`, with **custom Python implementations** of retrieval metrics (Recall@5, MRR, Context Precision). No framework library is used as the active evaluation engine.

The harness now also supports **behavior-aware evaluation** for queries whose expected outcome is not an answer, such as `clarify`, `insufficient_context`, and `refuse_out_of_scope`. These cases are scored on whether the system took the correct action instead of being incorrectly penalised for having no retrieved chunks.

RAGAS and DeepEval are retained as installed dependencies for one specific reason: they are candidates for integration in a future iteration and keeping them installed means the integration can be validated without a separate environment setup step. They are not imported or called anywhere in the current codebase.

### Why LLM-as-judge over RAGAS

RAGAS was the primary framework candidate. It provides pre-built implementations of faithfulness, answer relevance, context recall, and context precision that are semantically equivalent to what this system computes. The reasons for not using it as the active evaluation engine:

**1. RAGAS requires reformatting pipeline outputs into its own data structures.** The pipeline returns `PipelineResult` objects with typed fields. RAGAS expects `Dataset` objects with specific column names (`question`, `answer`, `contexts`, `ground_truths`). Adding an adapter layer introduces a translation step that can silently drop or misformat data, and it couples the evaluation code to the RAGAS API surface — any RAGAS version bump can break evals without warning.

**2. RAGAS scoring prompts are not inspectable at the point of evaluation.** When a faithfulness score of 0.3 is returned, diagnosing whether it reflects a genuine hallucination or a prompt formatting issue requires reading RAGAS source code. The custom LLM-as-judge prompts in `src/eval/metrics.py` are fully visible and directly modifiable — the scoring rubric, the context formatting, and the output schema are all in the same file as the metric function. This matters for a POC where the prompt may need to be tuned.

**3. RAGAS uses its own LLM client configuration** and defaults to OpenAI with separate credential management. Since the pipeline already has `LLMClient` with a lazy-initialised OpenAI client, using RAGAS would introduce a second OpenAI client instance with potentially different model and temperature settings, making it harder to reason about evaluation consistency.

**4. The custom implementation is sufficient at this scale.** The brief requires faithfulness and answer relevance — both are implemented with explicit 0–1 scoring rubrics and JSON output parsing that handles code fences and malformed responses. The implementation is 80 lines of readable Python covering the full required surface area.

### Why LLM-as-judge over DeepEval

DeepEval provides a richer testing framework — pytest integration, assertion-style metric checks, CI/CD hooks, and a cloud dashboard for metric tracking. The reasons for not using it as the active engine:

**1. DeepEval's primary value is CI/CD integration, which is out of scope for a POC.** Its core strength is running evals as part of a test pipeline with pass/fail assertions and automated regression detection. For a POC evaluation harness that produces a printed report, this infrastructure is unnecessary overhead.

**2. DeepEval introduces a mandatory `EvaluationTestCase` wrapper** around every query that adds abstraction without adding capability at this scale.

**3. Both RAGAS and DeepEval would be strong choices for a production deployment** where metric reproducibility across environments, team visibility into score trends over time, and CI/CD integration matter. The custom implementation is the right tool for a POC; the framework libraries are the right tool for production. This is an intentional phased approach, not a quality judgment on the libraries themselves. Both are retained as dependencies specifically so this upgrade path requires no additional installation step.

### Why not LangSmith

LangSmith is an observability and tracing platform, not a metrics computation library. Its evaluation capabilities are secondary to its tracing functionality. Since the pipeline already implements full `TraceLog` observability with structured JSON logging accessible via the `/api/trace` endpoint and the demo UI trace panel, adding LangSmith would duplicate the tracing layer without adding metric computation capability. LangSmith becomes relevant when the team needs cross-request trend dashboards, shared team visibility into evaluation scores, and a persistent evaluation history — all production concerns, not POC requirements.

### Why not TruLens

TruLens is primarily designed for LangChain and LlamaIndex pipelines and requires wrapping the pipeline in TruLens instrumentation classes. The custom pipeline architecture does not use either framework, so adopting TruLens would require either significant instrumentation overhead or a compatibility shim. The value does not justify the integration cost at POC scale.

### Retrieval metrics — why custom implementation

RAGAS includes context recall and context precision implementations. These were not adopted for the same reasons as the generation metrics: the custom implementations in `RetrievalMetrics` are direct, readable, and do not require reformatting chunk ID lists into RAGAS data structures. Recall@5, MRR, and Context Precision are standard IR formulas with no meaningful quality difference between a custom implementation and a library implementation of the same formula.

For expected clarification/refusal cases, the harness avoids treating the absence of retrieved chunks as a retrieval failure. Instead, it computes behavior success from `expected_behavior` and the pipeline's answerability/scope decision. This prevents safe refusals from inflating hallucination rate.

### Alternatives summary

| Option | Verdict | Rationale |
|---|---|---|
| RAGAS (active) | Rejected | Data structure coupling; non-inspectable prompts; duplicate LLM client |
| RAGAS (installed, for future) | Accepted | Zero install cost for future integration; not imported |
| DeepEval (active) | Rejected | CI/CD value irrelevant at POC scale; appropriate for production |
| DeepEval (installed, for future) | Accepted | Same rationale as RAGAS; not imported |
| LangSmith | Rejected | Tracing platform, not a metrics library; duplicates existing TraceLog |
| TruLens | Rejected | Framework-specific instrumentation incompatible with custom pipeline |
| Custom LLM-as-judge | Accepted | Full control; inspectable prompts; uses existing LLMClient; sufficient at POC scale |

### Production evolution path

1. **Replace LLM-as-judge faithfulness** with `cross-encoder/nli-deberta-v3-base` — a local NLI model that runs in ~200ms at no API cost per eval query. See ADR-6 item 4.
2. **Integrate RAGAS** for standardised metric reporting and cross-run comparability, once pipeline outputs are stable enough to warrant a maintained adapter layer.
3. **Adopt LangSmith** for production observability when the team needs shared dashboards and cross-request trend analysis beyond what the current `TraceLog` provides.

### Requirements traceability

This decision addresses the brief's explicit requirement to explain evaluation tooling choices. The implemented metrics satisfy R14.1 (Recall@K), R14.2 (MRR), R14.3 (Context Precision), R15.1 (Faithfulness), R15.2 (Answer Relevance), and R15.3 (Hallucination Rate). The behavior-aware metrics extend this with explicit scoring for clarification/refusal cases that would otherwise be incorrectly counted as retrieval or hallucination failures.

---

## ADR-6: What I Would Do Differently with 2 Additional Weeks

1. **Expand the customer dataset beyond the current synthetic target of 25 profiles to 50+ profiles.** The panel-hardening pass added a broader target set of customer edge cases, including international orders, split shipments, partial returns, expiring loyalty points, community discounts, sale-event purchases, and cancelled orders. A production-grade eval suite should go further with adversarial and long-tail profiles: duplicate names, multiple open returns, mixed payment methods, gift returns, fraud-review holds, and incomplete tracking data.

2. **Implement semantic query caching.** Embed each incoming query and compare it against a cache of recent query embeddings using cosine similarity. If similarity exceeds 0.95, return the cached answer without running the pipeline. In a real customer support context, a high proportion of queries are near-duplicates. This alone could eliminate pipeline execution for 40-60% of production traffic.

3. **Add a self-evaluating retrieval loop.** After retrieval, if the top chunk's cross-encoder score falls below a confidence threshold, automatically reformulate the query (expand synonyms, rephrase from a different angle) and retry retrieval once before proceeding to generation. This addresses the vocabulary mismatch problem more robustly than HyDE alone.

4. **Replace LLM-as-judge faithfulness with a dedicated NLI model.** The current faithfulness guardrail uses a full GPT-4o call for claim verification, adding 2-3 seconds per query in the eval harness. A cross-encoder NLI model such as `cross-encoder/nli-deberta-v3-base` performs at comparable quality for claim-context entailment tasks, runs locally in under 200ms per query, and has no API cost.

5. **Complete the ONNX reranker export.** The dependencies (`optimum`, `onnxruntime`) and export instructions are already in place. The one-time export step and inference code swap would reduce reranker CPU latency from ~400ms to ~80ms with no quality tradeoff. This was deferred because the export requires running in the target environment.

6. **Add query-aware conversation history for retrieval.** The current multi-turn implementation injects conversation history into the generation prompt only. A more robust approach would use the LLM to rewrite ambiguous follow-up queries into standalone queries before retrieval — e.g. rewriting "What about for sale items?" into "What is the return policy for Final Sale items?" This would improve retrieval relevance for follow-up questions without increasing the prompt size.


---

## ADR-8: Evaluation Framework Design

### Context

The evaluation framework needs to measure both retrieval quality and generation quality. Popular frameworks like RAGAS and DeepEval provide pre-built metrics, but many of their generation metrics are themselves LLM-as-judge based — they call an LLM to evaluate another LLM's output.

### Decision

Use a custom evaluation harness with two categories of metrics:

**Deterministic retrieval metrics** (no LLM calls):
- Recall@5: proportion of expected chunks in the top-5 retrieved results
- MRR: Mean Reciprocal Rank of the first relevant chunk
- Context Precision: proportion of retrieved chunks that are relevant

These metrics are computed by comparing retrieved chunk IDs against ground-truth `expected_chunk_ids` in the test query suite. They are fast, reproducible, and free.

**LLM-as-judge generation metrics** (one LLM call each):
- Faithfulness: does the answer's claims trace back to the provided context?
- Answer Relevance: does the answer address the user's question?
- Hallucination Rate: proportion of answers with at least one unsupported claim

**Behavior and customer-context metrics** (deterministic/action-aware):
- Behavior Success Rate: whether expected clarification/refusal cases took the correct action
- Customer context usage: whether customer-profile evidence was available and used when required
- Order/item correctness fields: expected order ID, customer ID, product ID, and customer facts for structured customer queries

### Why not RAGAS/DeepEval directly

1. RAGAS and DeepEval metrics are largely LLM-as-judge based themselves — using them does not avoid the cost or non-determinism of LLM evaluation.
2. The ALO domain requires retail-specific evaluation rubrics: customer-order correctness, Final Sale policy grounding, refusal behavior for missing customer context. Generic frameworks do not cover these.
3. A custom harness allows failure triage by category (routing failure, retrieval miss, reranker failure, customer join failure) rather than just aggregate scores.
4. RAGAS and DeepEval remain available as optional dependencies (`pip install -e ".[eval-frameworks]"`) for future benchmarking comparisons.

### Rationale

Custom metrics give full control over what "correct" means in this domain. The deterministic retrieval metrics are the most trustworthy signal for answerable RAG questions; behavior-aware metrics are the most trustworthy signal for safe clarification/refusal cases; and LLM-as-judge metrics provide a useful but noisy generation quality estimate.


---

## ADR-9: Panel Evaluation Hardening Decisions

### Context

The initial hardening pass showed that the system had strong architectural components but could still fail in panel-visible ways: customer/order questions could reach generation without customer context, out-of-scope questions could be scored as hallucinations, policy questions could miss companion clauses, and retrieval/generation metrics could punish correct clarification behavior.

### Decision

Add explicit safety and evaluation controls around the existing RAG pipeline rather than adding another framework layer:

1. **Answerability gate before generation:** The pipeline now checks whether required evidence is present before prompt construction. Missing customer context triggers clarification. Missing required product/policy context triggers an insufficient-context response.
2. **Fail-closed faithfulness guardrail:** Malformed judge responses and verification errors no longer default to success. High-risk customer/policy answers fail closed when faithfulness cannot be verified.
3. **Evidence contract tracing:** Claim-level support is represented through `EvidenceClaim` records for auditability.
4. **Behavior-aware evaluation:** `expected_behavior` allows the harness to score clarification and out-of-scope refusal cases separately from normal answerable RAG questions.
5. **Domain-specific retrieval hardening:** Hard domain filters, fabric entity chunks, policy tags, companion policy expansion, and deterministic out-of-scope guards make the system less dependent on generic semantic similarity.
6. **Registry/vector-store safety:** For non-persistent Chroma startup, chunks marked unchanged in the registry are still re-upserted if vectors are missing, preventing silent dense-index degradation.

### Rationale

These changes shift the system from "retrieve and answer" toward an enterprise support assistant that can decide whether it should answer at all. That distinction matters for retail policy and customer-order workflows: a safe clarification is better than a fluent but unsupported answer. The changes also make the eval harness more honest by separating answerable QA quality from behavior correctness.

### Current measured signal

The latest smoke evaluation after hardening is not final production evidence, but it is useful as a regression checkpoint:

| Metric | Smoke eval |
|---|---:|
| Queries evaluated | 8 |
| Mean Recall@5 | 0.562 |
| Mean MRR | 0.562 |
| Mean Context Precision | 0.323 |
| Mean Faithfulness | 0.750 |
| Mean Answer Relevance | 0.762 |
| Hallucination Rate | 0.250 |
| Mean Latency | 8,654 ms |
| p50 Latency | 8,953 ms |
| p95 Latency | 10,959 ms |

The signal is mixed: answer relevance improved and latency is lower than earlier full-eval runs, but retrieval precision and hallucination rate still require work. Behavior Success Rate should only be interpreted when the selected eval subset contains explicit `expected_behavior != "answer"` cases; otherwise it should be displayed as `N/A`.

### Next step

Before production pilot, focus on retrieval precision rather than adding more architecture: inspect failed smoke/full queries, compare expected vs retrieved chunk IDs, tune policy companion expansion, and calibrate reranker thresholds per domain.