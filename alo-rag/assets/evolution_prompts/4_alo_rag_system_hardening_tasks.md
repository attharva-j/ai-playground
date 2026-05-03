# ALO RAG System — Panel Evaluation Hardening Task Brief

This document is a list of implementation-ready tasks for you who working on the ALO RAG System in teh `alo-rag` directory in the repository.

The goal is to make the project stronger for a Senior AI Engineer panel evaluation by improving architecture, retrieval quality, evaluation rigor, customer/policy safety, documentation accuracy, and production-readiness credibility.

---

## Agent Brief

You are working on the ALO RAG System repository. Your goal is to make the project stronger for a Senior AI Engineer panel evaluation.

Do not make superficial changes. These are conceptual improvements to the RAG architecture, evaluation framework, and production-readiness story. Prioritize correctness, traceability, and honest measured improvement over adding unnecessary complexity.

Important rules:

1. Do not fake or inflate metrics.
2. Do not update `expected_chunk_ids` just to improve retrieval metrics unless the current ground truth is objectively wrong and you document why.
3. Keep the system runnable from scratch.
4. Preserve existing code style and project structure.
5. Add or update tests for every behavior change.
6. Update documentation to distinguish what is implemented now vs what is planned.
7. Update `docs/CHANGELOG.md` following the existing format. Add a new section after `v0.10` with this heading:

   ```markdown
   ## v0.11 — Panel Evaluation Hardening (May 3, 2026)
   ```

   Under that section, follow the existing changelog style: use bold subsections such as `**Problem identified:**`, `**Root cause:**`, `**Change made:**`, `**Files changed:**`, and `**Evaluation impact:**`. Record every conceptual architecture/eval change made in this work.

Primary objective:

Improve the repo so it more convincingly meets the take-home assignment expectations for a production-grade retail RAG system: better retrieval precision, safer customer/policy answering, clearer evaluation, lower latency story, stronger failure analysis, and better alignment between code and docs.

---

# Detailed Task List

## Task 1 — Create a baseline before changing anything

**Goal:** Capture the current behavior so improvements/regressions are measurable.

**Files likely touched:**

- `evals/baseline.json`
- `docs/failure_analysis.md`
- optionally `evals/results_*.json`

**Instructions:**

1. Run the current eval harness.
2. Save raw per-query results to a timestamped JSON file.
3. Save the current results as the regression baseline using the existing regression harness if supported.
4. Compute and record:
   - mean Recall@5
   - mean MRR
   - mean Context Precision
   - mean Faithfulness
   - mean Answer Relevance
   - Hallucination Rate
   - mean latency
   - p50 latency
   - p95 latency
5. Add p50 and p95 latency calculation if not already present.

**Acceptance criteria:**

- There is a reproducible baseline file.
- The eval command still works.
- The final report clearly distinguishes baseline metrics from post-change metrics.

---

## Task 2 — Fix documentation/tooling mismatch around RAGAS, DeepEval, and custom LLM-as-judge

**Problem:** The README currently implies RAGAS/DeepEval are the evaluation stack, but the implementation is primarily custom deterministic retrieval metrics plus custom LLM-as-judge generation metrics.

**Files likely touched:**

- `README.md`
- `docs/ADR.md`
- `docs/production_readiness_memo.md`
- `src/eval/metrics.py`
- optionally `pyproject.toml`

**Instructions:**

1. Update the tech stack table in `README.md`.
2. Replace vague “RAGAS, DeepEval” claims with:

   ```text
   Custom deterministic retrieval metrics + custom LLM-as-judge generation metrics; RAGAS/DeepEval-compatible design for optional future benchmarking.
   ```

3. In `docs/ADR.md`, add a short evaluation decision section:
   - Explain that RAGAS and DeepEval are useful frameworks.
   - Clarify that many RAGAS/DeepEval metrics are themselves LLM-as-judge based.
   - Explain why this project uses a custom judge harness: retail-specific rubrics, customer-order correctness, refusal behavior, policy grounding, and failure triage.
   - Make clear that retrieval metrics are deterministic when expected chunk IDs exist.
4. If dependencies include RAGAS/DeepEval but are unused, either:
   - remove them, or
   - mark them as optional/future adapters.
5. Do not overclaim.

**Acceptance criteria:**

- A reviewer does not come away thinking the repo uses RAGAS/DeepEval when it does not.
- The explanation sounds technically mature: “custom domain-specific judge over generic defaults,” not “LLM-as-judge versus RAGAS.”

---

## Task 3 — Expand customer dataset to satisfy the assignment

**Problem:** The assignment expects a structured customer dataset of roughly 20–50 synthetic customers. The current dataset has only 8.

**Files likely touched:**

- `data/customers/customer_order_history.json`
- `data/README.md`
- `README.md`
- `evals/test_queries.json`
- `tests/test_generation.py`
- `tests/test_pipeline.py`

**Instructions:**

1. Expand customer profiles from 8 to at least 25.
2. Add customers covering meaningful retail edge cases:
   - standard return-eligible purchase
   - final sale item
   - discounted item
   - order outside return window
   - order inside return window
   - partial return
   - return requested / pending
   - exchange completed
   - split shipment
   - cancelled order
   - international customer
   - loyalty tier customer
   - customer with expired points
   - customer who used military/community discount
   - customer with multiple seasonal purchases
3. Keep all data synthetic.
4. Update README/data docs with the new customer count.
5. Add 4–6 new eval queries that require structured customer lookup.

**Acceptance criteria:**

- Customer dataset has at least 25 profiles.
- Existing customer tests still pass.
- Customer eval queries cover both answerable and unanswerable cases.
- No customer data is embedded into the vector store.

---

## Task 4 — Add an answerability gate before generation

**Problem:** The system can proceed to generation even when required evidence is missing, especially for customer/order queries.

**Files likely touched:**

- `src/pipeline.py`
- `src/models.py`
- `src/generation/prompt_builder.py`
- `src/generation/customer_context.py`
- `tests/test_pipeline.py`
- `tests/test_generation.py`
- `evals/test_queries.json`

**Instructions:**

Implement a pre-generation answerability decision object.

Suggested model:

```python
@dataclass
class AnswerabilityDecision:
    answerable: bool
    required_evidence: list[str]
    available_evidence: list[str]
    missing_evidence: list[str]
    confidence: float
    reason: str
    action: Literal["answer", "clarify", "refuse_insufficient_context"]
```

The gate should run after classification, customer lookup, and retrieval, but before prompt generation.

Rules:

1. If primary domain is `customer` and `customer_id is None`, short-circuit with a clarifying answer.
2. If query asks for order status, return status, return eligibility, purchase history, or loyalty account details and no customer profile is available, do not generate from product/policy context.
3. If retrieved chunks do not include the required domain, do not generate a confident answer.
4. If top retrieved context scores are below a threshold, return an insufficient-context response.
5. If cross-domain query requires both customer and policy evidence, require both.
6. Include the answerability decision in the pipeline result trace.

Example response when customer ID is missing:

```text
I can help with that, but I need the customer profile or order context first. I do not have enough information to determine your order status from the product or policy knowledge base alone.
```

**Acceptance criteria:**

- Queries like “What is the status of my order?” do not hit generic retrieval when no customer ID is present.
- Queries requiring customer context do not hallucinate order or return status.
- Eval harness can record answerability decisions.
- Tests cover customer missing-context behavior.

---

## Task 5 — Make the faithfulness guardrail fail closed for high-risk cases

**Problem:** The current guardrail returns an empty claim list if claim extraction fails, which can accidentally score as fully faithful. Also, after regeneration, unsupported claims may still pass through.

**Files likely touched:**

- `src/generation/guardrails.py`
- `src/models.py`
- `src/pipeline.py`
- `tests/test_generation.py`
- `tests/test_pipeline.py`

**Instructions:**

1. Change claim extraction failure behavior:
   - Do not return `[]` and treat it as faithful.
   - Return a verification error state.
2. Add status to `FaithfulnessResult`, for example:
   - `passed`
   - `failed_unsupported_claims`
   - `failed_verification_error`
   - `failed_no_context`
3. For high-risk domains (`policy`, `customer`, `cross-domain`):
   - If verification fails, return a safe insufficient-context answer.
   - Do not return unverified generated content.
4. For low-risk product queries:
   - You may return the answer with a warning if verification fails, but this behavior must be explicit.
5. If regenerated answer still contains unsupported claims:
   - Do not silently return it as final for customer/policy queries.
   - Return a safe fallback or a minimal answer containing only supported claims.
6. Add tests where:
   - judge JSON parsing fails,
   - no context is available,
   - regenerated answer still has unsupported claims.

**Acceptance criteria:**

- Guardrail no longer treats parse failure as success.
- Policy/customer hallucinations decrease.
- The pipeline exposes guardrail status in trace output.

---

## Task 6 — Introduce an evidence contract for generated answers

**Goal:** Make the system more enterprise-grade and auditable.

**Files likely touched:**

- `src/models.py`
- `src/generation/guardrails.py`
- `src/generation/prompt_builder.py`
- `src/pipeline.py`
- `demo/app/page.tsx`
- `tests/test_generation.py`

**Instructions:**

Add an internal evidence contract representation.

Suggested schema:

```python
@dataclass
class EvidenceClaim:
    claim: str
    evidence_type: Literal["product", "policy", "customer", "none"]
    source_id: str | None
    supported: bool
    risk_level: Literal["low", "medium", "high"]
```

Use it to map important answer claims to source chunks or customer records.

For customer/order claims, support should come from structured customer context, not only retrieved chunks.

For policy claims, support should come from policy chunks.

Expose this in the trace/UI as an “Evidence Checklist.”

**Acceptance criteria:**

- The final pipeline result includes claim-level evidence support.
- UI can show which claims are supported.
- Customer-specific claims are verified against customer profile data.
- Policy claims are verified against policy chunks.

---

## Task 7 — Improve retrieval precision with stronger domain filtering

**Problem:** Context Precision is too low. The system often sends irrelevant chunks to generation.

**Files likely touched:**

- `src/retrieval/hybrid_search.py`
- `src/pipeline.py`
- `src/query/intent_router.py`
- `src/models.py`
- `tests/test_retrieval.py`
- `evals/test_queries.json`

**Instructions:**

1. Use hard metadata filters for clear single-domain queries:
   - product query → product chunks only
   - policy query → policy chunks only
   - customer query → structured customer lookup plus only policy/product chunks if needed
2. Use soft expansion only for cross-domain queries.
3. Add trace fields:
   - primary domain
   - metadata filter used
   - pre-filter result count
   - post-filter result count
   - pre-rerank top chunks
   - post-rerank top chunks
4. Add a configurable domain confidence threshold.
5. If domain classification confidence is low, use broader retrieval but reduce generation confidence and require stronger answerability checks.

**Acceptance criteria:**

- Context Precision improves over baseline.
- Product-only queries no longer retrieve irrelevant policy chunks unless explicitly needed.
- Policy-only queries do not retrieve product chunks unless query is cross-domain.
- Retrieval trace makes filtering decisions visible.

---

## Task 8 — Add fabric/entity-level retrieval for product comparisons

**Problem:** Queries like “What’s the difference between Airlift and Airbrush fabric?” should be easy, but they fail or rely on product chunks that may not contain clean comparison-level evidence.

**Files likely touched:**

- `src/ingestion/loaders.py`
- `src/ingestion/chunkers.py`
- `src/models.py`
- `data/products/alo_product_catalog.json`
- `tests/test_retrieval.py`
- `evals/test_queries.json`

**Instructions:**

1. Create first-class fabric glossary chunks, not only enriched product chunks.
2. Each fabric glossary chunk should include:
   - fabric name
   - composition
   - compression level
   - finish
   - use cases
   - key properties
   - associated product IDs
3. Assign deterministic chunk IDs:
   - `fabric-airlift`
   - `fabric-airbrush`
   - etc.
4. Add metadata:
   - `domain: product`
   - `entity_type: fabric`
   - `fabric_name`
5. Modify retrieval so comparison queries involving two fabrics boost fabric entity chunks.
6. Add a lightweight entity extractor for known fabric names.

**Acceptance criteria:**

- Fabric comparison queries retrieve both relevant fabric chunks in top 5.
- TQ-002 or equivalent query improves materially.
- Product chunks remain useful, but fabric glossary chunks become the primary evidence for fabric-level questions.

---

## Task 9 — Add policy metadata tags and companion chunks

**Problem:** Some policy questions require two related sections. Reranking isolated chunks can miss multi-section logic.

**Files likely touched:**

- `src/ingestion/chunkers.py`
- `src/ingestion/loaders.py`
- `src/retrieval/hybrid_search.py`
- `src/pipeline.py`
- `tests/test_retrieval.py`
- `evals/test_queries.json`

**Instructions:**

1. Add policy metadata tags during ingestion:
   - `return_window`
   - `final_sale`
   - `community_discount`
   - `sale_restriction`
   - `loyalty_points`
   - `promo_stacking`
   - `shipping_sla`
2. Use keyword/entity detection to boost matching tags.
3. Implement companion chunk retrieval:
   - If a community discount chunk is retrieved and query mentions a sale event, also include sale restriction/promo stacking chunk.
   - If a final sale chunk is retrieved and query asks return eligibility, also include return window/exceptions chunk.
4. Companion chunks should be traceable as `retrieval_reason: companion_chunk`.

**Acceptance criteria:**

- Cross-section policy queries retrieve all required sections.
- TQ-018-style questions improve.
- The trace clearly shows when a companion chunk was added and why.

---

## Task 10 — Implement parent-child retrieval or section expansion

**Problem:** Small chunks help retrieval, but generation sometimes needs the broader parent section.

**Files likely touched:**

- `src/ingestion/chunkers.py`
- `src/models.py`
- `src/retrieval/hybrid_search.py`
- `src/pipeline.py`
- `tests/test_retrieval.py`

**Instructions:**

1. Add parent IDs to chunks:
   - policy document ID
   - section ID
   - subsection ID
2. Retrieve small chunks for ranking.
3. After reranking, expand top chunks to parent section where appropriate.
4. Avoid dumping entire long policy docs into the prompt.
5. Preserve chunk-level citations.

**Acceptance criteria:**

- Retrieval precision does not drop.
- Generation receives enough context for multi-clause policy answers.
- Context token count remains bounded.

---

## Task 11 — Fix vector store and registry lifecycle correctness

**Problem:** The registry may say chunks are unchanged while the vector store is empty or using a different embedding model/index lifecycle.

**Files likely touched:**

- `src/ingestion/registry.py`
- `src/ingestion/index_builder.py`
- `src/ingestion/run_ingestion.py`
- `src/retrieval/hybrid_search.py`
- `server.py`
- `tests/test_retrieval.py`

**Instructions:**

1. Store index metadata:
   - embedding model name
   - embedding dimension
   - vector store collection name
   - index build ID
   - source content hash
2. On startup, validate:
   - vector store exists,
   - vector count matches registry active chunk count,
   - embedding dimension matches,
   - embedding model matches.
3. If using in-memory Chroma:
   - do not skip upserting vectors just because registry says chunks are unchanged.
4. If using persistent Chroma:
   - registry and vector store must share the same lifecycle.
5. Add a recovery path:
   - if registry/vector store mismatch is detected, rebuild the vector index or upsert missing chunks.
6. Add logs explaining whether startup is using incremental update or full rebuild.

**Acceptance criteria:**

- No silent dense retrieval degradation due to registry/vector mismatch.
- Tests cover empty vector store + populated registry.
- Startup logs are clear and trustworthy.

---

## Task 12 — Add structured customer-domain evaluation metrics

**Problem:** Customer questions are not well represented by generic vector retrieval metrics alone.

**Files likely touched:**

- `src/eval/metrics.py`
- `src/eval/harness.py`
- `src/models.py`
- `evals/test_queries.json`
- `tests/test_eval.py`

**Instructions:**

Add customer-specific eval fields to test queries.

Suggested schema additions:

```json
{
  "expected_customer_id": "CUST-10177",
  "expected_order_id": "ORD-...",
  "expected_product_id": "M6801R-BLK",
  "expected_customer_facts": {
    "return_status": "Return Requested — Pending",
    "return_eligible": true
  },
  "requires_customer_context": true,
  "expected_behavior": "answer|clarify|insufficient_context"
}
```

Add metrics:

- `customer_record_found`
- `correct_order_identified`
- `correct_item_identified`
- `return_eligibility_correct`
- `order_status_correct`
- `missing_customer_context_handled`
- `customer_context_used`

**Acceptance criteria:**

- Customer eval no longer depends only on retrieved chunk IDs.
- Missing customer context can score positively when the system correctly asks for clarification.
- Cross-domain customer-policy queries evaluate both structured and retrieved evidence.

---

## Task 13 — Add smoke and full eval modes

**Problem:** The assignment expects a regression harness that can run quickly. Current full eval latency makes the under-5-minute claim questionable.

**Files likely touched:**

- `src/eval/__main__.py`
- `src/eval/harness.py`
- `src/eval/regression.py`
- `evals/test_queries.json`
- `README.md`

**Instructions:**

1. Add CLI flags:
   - `--mode smoke`
   - `--mode full`
   - `--save-baseline`
   - `--compare-baseline`
   - `--output evals/results_<timestamp>.json`
2. Smoke mode should run 6–8 representative queries:
   - product
   - policy
   - customer
   - cross-domain
   - one missing-context query
   - one known historically failing query
3. Full mode should run all 25+ queries.
4. Add optional judge-response caching for evals.
5. Print:
   - p50 latency
   - p95 latency
   - cost estimate if feasible
   - number of LLM calls by type

**Acceptance criteria:**

- `python -m src.eval --mode smoke` runs under 5 minutes.
- `python -m src.eval --mode full` runs all queries.
- README clearly states which mode satisfies quick regression testing.

---

## Task 14 — Improve latency instrumentation and production-readiness accuracy

**Problem:** Actual eval latency is much higher than the production memo’s target latency story.

**Files likely touched:**

- `src/pipeline.py`
- `src/models.py`
- `src/eval/harness.py`
- `docs/production_readiness_memo.md`
- `README.md`

**Instructions:**

1. Record stage-level latency consistently:
   - classification
   - scope guard
   - HyDE
   - decomposition
   - embedding
   - retrieval
   - reranking
   - customer lookup
   - generation
   - faithfulness verification
   - regeneration if triggered
2. Add aggregate latency reporting:
   - mean
   - p50
   - p95
3. Update production memo with measured latency, not aspirational values.
4. Add optimization plan:
   - skip HyDE unless needed,
   - skip decomposition for simple queries,
   - use rule-based fast path for obvious product/customer queries,
   - cache judge calls in eval,
   - use async guardrail verification for low-risk demo answers,
   - local NLI model for claim verification,
   - ONNX reranker export.

**Acceptance criteria:**

- The production memo no longer conflicts with eval output.
- Reviewers can see exactly where latency is coming from.
- Latency optimization plan is specific and credible.

---

## Task 15 — Add query fast paths to reduce unnecessary LLM calls

**Problem:** The system likely uses too many LLM calls for routing, HyDE, decomposition, generation, guardrails, and eval judging.

**Files likely touched:**

- `src/query/intent_router.py`
- `src/query/decomposer.py`
- `src/query/hyde.py`
- `src/pipeline.py`
- `tests/test_query_intelligence.py`

**Instructions:**

1. Add rule-based fast paths before LLM classification:
   - known fabric/product names → product
   - “return”, “exchange”, “shipping”, “promo”, “discount”, “loyalty” → policy
   - “my order”, “my return”, “what did I buy”, “my points” → customer
2. Only call LLM classifier if rules are ambiguous.
3. Only run decomposition if query genuinely needs multiple domains.
4. Only run HyDE for policy queries above threshold or explicit policy language.
5. Add trace fields indicating whether fast path or LLM path was used.

**Acceptance criteria:**

- Simple queries avoid unnecessary LLM calls.
- Latency improves for easy product and customer queries.
- Routing accuracy does not regress.

---

## Task 16 — Add missing-context and refusal test cases

**Problem:** Safe behavior must be evaluated, not just happy-path answering.

**Files likely touched:**

- `evals/test_queries.json`
- `src/eval/metrics.py`
- `tests/test_eval.py`

**Instructions:**

Add test queries for:

1. Customer order status without customer ID.
2. Return eligibility without customer ID.
3. Product not in catalog.
4. Policy that does not exist.
5. Medical/legal/financial out-of-scope question.
6. Prompt injection attempt asking to ignore context.
7. Request for another customer’s order.
8. Ambiguous product name.

For each, define expected behavior:

- `clarify`
- `insufficient_context`
- `refuse_out_of_scope`
- `answer_with_caveat`

**Acceptance criteria:**

- The system can score safe refusal/clarification as success.
- Hallucination rate is not penalized incorrectly when the system refuses properly.
- Failure analysis distinguishes “retrieval failed” from “system correctly refused.”

---

## Task 17 — Update failure analysis to be trace-grounded and current

**Problem:** Current failure analysis may not match the latest eval output and is not always tied to pipeline traces.

**Files likely touched:**

- `docs/failure_analysis.md`
- `src/eval/failure_analysis.py`
- `src/eval/harness.py`

**Instructions:**

1. Regenerate failure analysis after changes.
2. For the 3 worst queries, include:
   - query
   - expected behavior
   - actual answer
   - retrieved chunk IDs
   - missing expected chunks
   - domain classification
   - answerability decision
   - guardrail status
   - root cause category
   - remediation
3. Classify failures into:
   - routing failure
   - retrieval miss
   - reranker failure
   - context pollution
   - generation failure
   - guardrail failure
   - customer join failure
   - eval-data issue
4. Ensure `docs/failure_analysis.md` matches the latest metrics.

**Acceptance criteria:**

- The failure analysis is honest and specific.
- It does not claim a failure is fixed unless eval shows it.
- It helps a reviewer understand where the system breaks.

---

## Task 18 — Add an “Implemented vs Planned” section to docs

**Problem:** Some docs currently describe planned production behavior as if it already exists.

**Files likely touched:**

- `README.md`
- `docs/ADR.md`
- `docs/production_readiness_memo.md`

**Instructions:**

Add an `Implemented vs Planned` section.

Separate features into:

**Implemented now:**

- domain-aware chunking
- hybrid dense/BM25 retrieval
- RRF fusion
- reranking
- structured customer lookup
- custom eval harness
- demo UI
- answerability gate, once implemented
- evidence contract, once implemented

**Planned / production extension:**

- managed vector DB
- full event-driven incremental indexing
- production authZ/authN
- human feedback loop
- large-scale policy versioning
- online monitoring
- semantic answer cache
- NLI-based faithfulness verification

**Acceptance criteria:**

- Docs do not overstate implementation.
- Reviewers can clearly distinguish POC scope from production roadmap.

---

## Task 19 — Add bitemporal policy metadata as an enterprise differentiator

**Goal:** Add a lightweight but impressive production-grade capability for policy staleness and seasonal rules.

**Files likely touched:**

- `data/policies/*.md`
- `src/ingestion/chunkers.py`
- `src/models.py`
- `src/retrieval/hybrid_search.py`
- `evals/test_queries.json`
- `docs/ADR.md`
- `docs/production_readiness_memo.md`

**Instructions:**

1. Add policy metadata:
   - `policy_version`
   - `effective_from`
   - `effective_to`
   - `season`
2. Add retrieval filtering by effective date where query includes temporal language:
   - “holiday policy”
   - “during Cyber Monday”
   - “last season”
   - “current return policy”
3. Add at least 2 eval queries that require policy-time awareness.
4. Keep implementation lightweight; do not overbuild a full rules engine.

**Acceptance criteria:**

- Seasonal/stale policy behavior is represented.
- Production memo explains how this addresses staleness/compliance risk.
- Queries can prefer currently effective policy chunks.

---

## Task 20 — Update the demo UI trace panel

**Goal:** Make the UI more compelling for the panel.

**Files likely touched:**

- `server.py`
- `demo/app/page.tsx`
- `src/models.py`
- `src/pipeline.py`

**Instructions:**

Expose in the UI:

1. Domain classification.
2. Query fast path vs LLM route.
3. Answerability decision.
4. Retrieved chunks.
5. Companion chunks.
6. Customer context used/not used.
7. Evidence contract.
8. Guardrail status.
9. Stage-level latency.

**Acceptance criteria:**

- The demo helps tell the production-readiness story.
- A reviewer can see why the system answered, clarified, or refused.
- The trace does not expose sensitive customer data unnecessarily.

---

## Task 21 — Add tests for all architecture changes

**Files likely touched:**

- `tests/test_pipeline.py`
- `tests/test_retrieval.py`
- `tests/test_eval.py`
- `tests/test_generation.py`
- `tests/test_query_intelligence.py`

**Required test coverage:**

1. Missing customer ID short-circuits order-status query.
2. Customer query with valid customer ID uses structured context.
3. Product fabric comparison retrieves fabric entity chunks.
4. Policy query uses hard policy filter.
5. Cross-domain query allows multiple domains.
6. Guardrail parse failure fails closed.
7. Empty vector store + populated registry triggers rebuild/upsert.
8. Smoke eval mode selects correct subset.
9. Customer-specific metrics score correctly.
10. Safe refusal is scored as correct behavior where expected.

**Acceptance criteria:**

- `pytest` passes.
- New tests fail on the old behavior and pass on the new behavior where practical.
- Tests avoid external API calls by mocking LLM/embedding clients where possible.

---

## Task 22 — Produce final post-change evaluation summary

**Files likely touched:**

- `docs/failure_analysis.md`
- `README.md`
- `docs/production_readiness_memo.md`
- `evals/results_*.json`
- `docs/CHANGELOG.md`

**Instructions:**

After implementing changes:

1. Run smoke eval.
2. Run full eval if API budget allows.
3. Compare against baseline.
4. Add a concise before/after table:

```markdown
| Metric | Baseline | After | Delta |
|---|---:|---:|---:|
| Recall@5 | ... | ... | ... |
| MRR | ... | ... | ... |
| Context Precision | ... | ... | ... |
| Faithfulness | ... | ... | ... |
| Answer Relevance | ... | ... | ... |
| Hallucination Rate | ... | ... | ... |
| Mean Latency | ... | ... | ... |
| p50 Latency | ... | ... | ... |
| p95 Latency | ... | ... | ... |
```

5. Be honest if a metric regresses.
6. Explain why the tradeoff is acceptable or how to address it next.

**Acceptance criteria:**

- Final docs include measured evidence of improvement.
- Changelog records all major conceptual changes.
- README tells the reviewer exactly how to run smoke and full evals.

---

# Required `CHANGELOG.md` Update Format

Add this section after `v0.10`:

```markdown
---

## v0.11 — Panel Evaluation Hardening (May 3, 2026)

**Problem identified:** The architecture was strong, but panel-readiness gaps remained: low context precision, high hallucination rate, customer queries without answerability gating, evaluation/documentation mismatches, latency reporting gaps, and insufficient customer-domain evaluation depth.

**Root cause:** The system could proceed to generation when required evidence was missing; retrieval filtering was too permissive for single-domain queries; customer correctness was evaluated mostly through generic retrieval/generation metrics; and some documentation described production-intended behavior more strongly than the current implementation supported.

**Change made:** 
- Added pre-generation answerability gating for customer, policy, and cross-domain queries.
- Made faithfulness verification fail closed for high-risk domains.
- Added evidence-contract tracing for generated claims.
- Improved domain-specific retrieval filtering and policy/fabric entity retrieval.
- Expanded customer dataset and customer-specific eval metrics.
- Added smoke/full eval modes with latency percentiles and regression comparison.
- Updated documentation to clearly separate implemented behavior from production roadmap.

**Files changed:**
- `src/pipeline.py`
- `src/models.py`
- `src/generation/guardrails.py`
- `src/generation/prompt_builder.py`
- `src/retrieval/hybrid_search.py`
- `src/ingestion/loaders.py`
- `src/ingestion/chunkers.py`
- `src/eval/harness.py`
- `src/eval/metrics.py`
- `evals/test_queries.json`
- `data/customers/customer_order_history.json`
- `README.md`
- `docs/ADR.md`
- `docs/failure_analysis.md`
- `docs/production_readiness_memo.md`

**Evaluation impact:** Record actual before/after metrics here after running the eval. Include Recall@5, MRR, Context Precision, Faithfulness, Answer Relevance, Hallucination Rate, mean latency, p50 latency, and p95 latency.

**Why this matters:** These changes move the system from a feature-rich RAG POC toward a more production-credible enterprise assistant: it knows when it can answer, when it should not answer, what evidence supports each claim, and how changes affect measurable quality.
```

Adjust the `Files changed` list to match the actual files modified. Do not list files that were not changed.

---

# Recommended Priority Order

Use this order if time is limited:

1. Answerability gate
2. Fail-closed guardrail
3. Docs/tooling mismatch cleanup
4. Smoke/full eval mode
5. Customer-specific metrics
6. Fabric glossary chunks
7. Policy metadata/companion chunks
8. Registry/vector lifecycle fix
9. UI trace improvements
10. Bitemporal policy metadata

The highest ROI changes are answerability gating, guardrail behavior, eval clarity, and docs alignment. Those directly address the biggest panel risks: hallucination, customer-query safety, latency credibility, and whether the evaluation story is believable.

---

# Suggested Final Reviewer Narrative

After completing the work, the repo should support this story:

> The initial eval exposed low context precision, high hallucination rate, and latency gaps. I used the failure analysis to add answerability gating, fail-closed guardrails, customer-specific metrics, stronger retrieval filtering, and evidence-contract tracing. The system now better distinguishes answerable from unanswerable cases, grounds customer and policy claims more explicitly, and provides a smoke regression path for fast iteration.

This is the narrative a senior AI panel will care about: not just that the system has many RAG features, but that the architecture, implementation, and evaluation loop reinforce each other.
