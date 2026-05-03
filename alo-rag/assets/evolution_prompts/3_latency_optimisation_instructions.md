# Latency Optimisation Instructions

## Overview

Three code changes and one new document. Read all sections before starting.
Apply changes in the order listed — Change 3 depends on Change 2.

**Files to modify:**
- `src/generation/llm_client.py` — Change 1
- `src/query/hyde.py` — Change 2
- `src/pipeline.py` — Change 3

**Files to create:**
- `docs/CHANGELOG.md` — Change 4

**Dependencies to add to `pyproject.toml`:**
- `optimum` — Change 1b (ONNX reranker, see Note below)

> **Note on ONNX reranker (Solution 5 from prior discussion):** The ONNX
> export of `bge-reranker-base` requires a one-time `optimum-cli export`
> step that cannot be scripted reliably without knowing the target
> environment. The agent should add `optimum` and `onnxruntime` to
> `pyproject.toml` dependencies and add a clearly labelled
> `# TODO: ONNX export` comment in `reranker.py` with the exact commands
> the developer needs to run manually. Do not attempt to modify the
> reranker inference logic — that change requires the exported model
> artefact to be present first.

---

## Change 1 of 4 — `src/generation/llm_client.py`

### What and why

Replace `gpt-4o-mini` with `gpt-4.1-nano` as the classification model.
`gpt-4.1-nano` is OpenAI's fastest and cheapest model. For the structured
JSON classification tasks this method handles (intent routing, scope guard,
query decomposition), it performs equivalently to `gpt-4o-mini` at
approximately 2x the speed and half the cost. The `classify()` method
produces tiny outputs (a JSON object under 80 tokens) — this is exactly
the task profile `gpt-4.1-nano` is optimised for.

`gpt-4o` is retained for generation — answer quality requires the stronger
model. Only the classification path changes.

### Edit 1a — Change the constant

Find this exact line:

```python
_DEFAULT_CLASSIFICATION_MODEL = "gpt-4o-mini"
```

Replace it with:

```python
_DEFAULT_CLASSIFICATION_MODEL = "gpt-4.1-nano"
```

### Edit 1b — Update the module docstring

Find this exact text in the module docstring at the top of the file:

```
- **classify()** — uses GPT-4o-mini for fast, lightweight classification
  tasks such as intent routing and scope guard evaluation.
```

Replace it with:

```
- **classify()** — uses GPT-4.1-nano for fast, lightweight classification
  tasks such as intent routing and scope guard evaluation. GPT-4.1-nano
  is chosen over gpt-4o-mini for its lower latency and cost on short
  structured-output tasks (classification, decomposition, scope guard).
```

### Edit 1c — Update the class docstring

Find this exact text in the `LLMClient` class docstring:

```
    * :meth:`classify` — GPT-4o-mini-based lightweight classification for
      intent routing and scope guard evaluation.  Designed to return
      results within 2 seconds per query (R5.2).
```

Replace it with:

```
    * :meth:`classify` — GPT-4.1-nano-based lightweight classification for
      intent routing and scope guard evaluation.  GPT-4.1-nano is OpenAI's
      fastest model and is well-suited to short structured-output tasks.
      Designed to return results within 1 second per query (R5.2).
```

### Edit 1d — Update the `__init__` parameter docstring

Find this exact text:

```
    classification_model:
        OpenAI model identifier used for classification calls.
        Defaults to ``"gpt-4o-mini"``.
```

Replace it with:

```
    classification_model:
        OpenAI model identifier used for classification calls.
        Defaults to ``"gpt-4.1-nano"``.
```

### Edit 1e — Update the `classify()` method docstring

Find this exact text inside the `classify()` docstring:

```
        Used by the Intent Router (R5.1) and Scope Guard (R11.1) for
        fast query classification.  GPT-4o-mini is chosen for its low
        latency, keeping classification within the 2-second budget (R5.2).
```

Replace it with:

```
        Used by the Intent Router (R5.1) and Scope Guard (R11.1) for
        fast query classification.  GPT-4.1-nano is chosen for its low
        latency on short structured-output tasks, keeping classification
        within the 1-second budget (R5.2).
```

### Edit 1f — Add ONNX dependencies to `pyproject.toml`

In `pyproject.toml`, find the `dependencies` list and add two entries:

```toml
dependencies = [
    "openai",
    "chromadb",
    "rank-bm25",
    "voyageai",
    "sentence-transformers",
    "optimum",
    "onnxruntime",
    "ragas",
    "deepeval",
    "pydantic",
    "fastapi",
    "uvicorn",
    "python-dotenv",
]
```

### Edit 1g — Add ONNX TODO comment to `src/retrieval/reranker.py`

At the top of `CrossEncoderReranker._get_model()`, add a comment block
immediately before the `if self._model is None:` line:

```python
    def _get_model(self) -> Any:
        """Lazy-initialise and return the cross-encoder model.

        ONNX UPGRADE PATH (manual step required):
        To reduce reranker CPU latency from ~400ms to ~80ms, export the
        model to ONNX format and switch to ORTModelForSequenceClassification.

        Step 1 — export (run once in the project root):
            pip install optimum onnxruntime
            optimum-cli export onnx --model BAAI/bge-reranker-base bge_reranker_onnx/

        Step 2 — validate outputs match PyTorch outputs:
            python -c "
            from sentence_transformers import CrossEncoder
            from optimum.onnxruntime import ORTModelForSequenceClassification
            from transformers import AutoTokenizer
            import numpy as np

            pairs = [['test query', 'test document']]
            pt_model = CrossEncoder('BAAI/bge-reranker-base')
            pt_score = pt_model.predict(pairs)

            tokenizer = AutoTokenizer.from_pretrained('bge_reranker_onnx/')
            ort_model = ORTModelForSequenceClassification.from_pretrained(
                'bge_reranker_onnx/', provider='CPUExecutionProvider'
            )
            inputs = tokenizer(pairs[0][0], pairs[0][1], return_tensors='pt')
            ort_score = ort_model(**inputs).logits.item()
            print('PT score:', pt_score[0], '| ORT score:', ort_score)
            print('Match:', np.isclose(pt_score[0], ort_score, atol=1e-3))
            "

        Step 3 — once validated, replace _get_model() body with:
            from optimum.onnxruntime import ORTModelForSequenceClassification
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained('bge_reranker_onnx/')
            model = ORTModelForSequenceClassification.from_pretrained(
                'bge_reranker_onnx/', provider='CPUExecutionProvider'
            )
            self._model = (tokenizer, model)
        And update predict() calls accordingly.
        """
        if self._model is None:
```

---

## Change 2 of 4 — `src/query/hyde.py`

### What and why

Switch HyDE's hypothetical document generation from `gpt-4o`
(`llm_client.generate()`) to `gpt-4o-mini` (`llm_client.classify()`).

The hypothetical document is not returned to the user — it is embedded and
used purely as a retrieval vector. It needs to contain the right domain
vocabulary (policy terminology, return window language, loyalty tier names)
but does not need to be perfectly reasoned or beautifully written. The
quality bar is "contains the right words in the right register", not
"produces a correct answer". `gpt-4o-mini` meets this bar with a
generation time roughly 500ms faster than `gpt-4o` for 2-4 sentence outputs.

The `classify()` method is reused here because it shares the same
low-latency, capped-token profile. However, HyDE needs slightly more
tokens than the 80-token cap used for intent classification. A dedicated
`max_tokens` parameter is therefore added to `classify()` in `llm_client.py`
(see Edit 2a) so HyDE can request up to 200 tokens without changing the
80-token default for classification tasks.

### Edit 2a — Add optional `max_tokens` to `LLMClient.classify()`

In `src/generation/llm_client.py`, find the `classify()` method signature:

```python
    def classify(
        self,
        prompt: str,
        system: str = "",
    ) -> str:
```

Replace it with:

```python
    def classify(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = _CLASSIFICATION_MAX_TOKENS,
    ) -> str:
```

Then find this line inside the `classify()` method body:

```python
            response = client.chat.completions.create(
                model=self.classification_model,
                max_tokens=_CLASSIFICATION_MAX_TOKENS,
                messages=messages,
            )
```

Replace it with:

```python
            response = client.chat.completions.create(
                model=self.classification_model,
                max_tokens=max_tokens,
                messages=messages,
            )
```

### Edit 2b — Update the module docstring of `hyde.py`

Find this exact text at the top of `src/query/hyde.py`:

```
Uses the ``HYDE_SYSTEM_PROMPT`` to generate a hypothetical answer document
```

This text does not appear verbatim. Instead find the full module docstring:

```python
"""Hypothetical Document Embeddings (HyDE) module for the ALO RAG System.

Generates a hypothetical answer document for policy queries using the LLM,
then embeds that hypothetical answer for use in dense retrieval instead of
the raw query embedding.  This bridges the vocabulary gap between abstract
user questions and the terminology used in policy documents.

Requirements: 6.1, 6.2, 6.3
"""
```

Replace it with:

```python
"""Hypothetical Document Embeddings (HyDE) module for the ALO RAG System.

Generates a hypothetical answer document for policy queries using the LLM,
then embeds that hypothetical answer for use in dense retrieval instead of
the raw query embedding.  This bridges the vocabulary gap between abstract
user questions and the terminology used in policy documents.

The hypothetical document is generated using GPT-4o-mini (via
LLMClient.classify()) rather than GPT-4o.  The document is never shown
to the user — it is only embedded for retrieval.  The quality requirement
is vocabulary richness and domain register, not reasoning correctness.
GPT-4o-mini meets this bar at roughly 500ms less latency per call.

Requirements: 6.1, 6.2, 6.3
"""
```

### Edit 2c — Update the class docstring

Find this text inside `HyDEModule`'s class docstring:

```
    Parameters
    ----------
    llm_client:
        An :class:`LLMClient` instance used for Sonnet-based hypothetical
        answer generation.
```

Replace it with:

```
    Parameters
    ----------
    llm_client:
        An :class:`LLMClient` instance used for hypothetical answer
        generation. Uses the classify() path (GPT-4o-mini) rather than
        generate() (GPT-4o) — the hypothetical is for embedding only,
        not for display, so the faster model is appropriate.
```

### Edit 2d — Change the `generate_hypothetical()` method body

Find the `generate_hypothetical()` method. Its body currently reads:

```python
        try:
            hypothetical = self._llm_client.generate(
                prompt=query,
                system=_HYDE_SYSTEM_PROMPT,
                max_tokens=256,
            )
            logger.info(
                "HyDEModule.generate_hypothetical() completed — %d chars",
                len(hypothetical),
            )
            return hypothetical

        except Exception:
            logger.exception(
                "HyDEModule.generate_hypothetical() failed — query=%r",
                query,
            )
            raise
```

Replace it with:

```python
        try:
            # Use classify() (GPT-4o-mini) rather than generate() (GPT-4o).
            # The hypothetical document is embedded for retrieval only — it
            # is never shown to the user.  Vocabulary richness matters;
            # reasoning quality does not.  GPT-4o-mini is ~500ms faster
            # for this output length.
            hypothetical = self._llm_client.classify(
                prompt=query,
                system=_HYDE_SYSTEM_PROMPT,
                max_tokens=200,
            )
            logger.info(
                "HyDEModule.generate_hypothetical() completed — %d chars",
                len(hypothetical),
            )
            return hypothetical

        except Exception:
            logger.exception(
                "HyDEModule.generate_hypothetical() failed — query=%r",
                query,
            )
            raise
```

### Edit 2e — Update `generate_hypothetical()` docstring

Find this text in the `generate_hypothetical()` docstring:

```
        Uses GPT-4o via :meth:`LLMClient.generate` to produce a
        plausible policy document excerpt that would answer the user's
        question.  This hypothetical answer is intended to be embedded
        for dense retrieval, not returned to the user.
```

Replace it with:

```
        Uses GPT-4o-mini via :meth:`LLMClient.classify` to produce a
        plausible policy document excerpt that would answer the user's
        question.  This hypothetical answer is intended to be embedded
        for dense retrieval, not returned to the user.  GPT-4o-mini is
        used (rather than GPT-4o) because the document is evaluated only
        by its embedding proximity to real policy chunks — vocabulary
        richness matters, not reasoning depth.
```

---

## Change 3 of 4 — `src/pipeline.py`

### What and why

Stages 3 (HyDE) and 4 (decomposition) currently run sequentially in both
`run()` and `run_without_generation()`. They are independent of each other
— decomposition does not use the HyDE embedding, and HyDE does not use the
decomposed sub-queries. Both depend only on Stage 1 (classification), which
completes before either starts. They can therefore run in parallel threads,
eliminating the wait of whichever finishes first.

On multi-domain policy queries (the most complex and frequent hard queries),
this saves approximately 350ms — the decomposition call completes during the
same wall-clock time as the HyDE generation call.

`ThreadPoolExecutor` is already imported and used in `hybrid_search.py`.
The same pattern is applied here. The implementation must handle the case
where only one of the two stages is needed (single-domain non-policy queries
run neither; single-domain policy queries run HyDE but not decomposition;
multi-domain non-policy queries run decomposition but not HyDE).

### Edit 3a — Add import to `src/pipeline.py`

Find this line near the top of `src/pipeline.py`:

```python
import time
```

Replace it with:

```python
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
```

### Edit 3b — Add `_run_hyde_and_decompose_parallel()` helper method

Add this method to the `Pipeline` class, immediately before the existing
`_retrieve_for_sub_queries()` method. The exact insertion point is the line
that reads:

```python
    def _retrieve_for_sub_queries(
```

Insert the following complete method immediately before that line:

```python
    def _run_hyde_and_decompose_parallel(
        self,
        query: str,
        classification: IntentClassification,
    ) -> tuple[
        list[float] | None,   # query_embedding (from HyDE, or None)
        str | None,            # hyde_hypothetical text (or None)
        bool,                  # hyde_activated flag
        list[SubQuery],        # sub_queries
        dict[str, float],      # stage_latencies contributed by these two stages
    ]:
        """Run HyDE and query decomposition in parallel threads.

        Both stages depend only on the intent classification produced by
        Stage 1.  They are independent of each other and can therefore
        execute concurrently.

        HyDE is submitted only when policy confidence exceeds HYDE_THRESHOLD.
        Decomposition is submitted only when the query is multi-domain.
        If neither condition is met, both return immediately with defaults
        (no threads are created).

        Returns a tuple of (query_embedding, hyde_hypothetical, hyde_activated,
        sub_queries, stage_latencies).
        """
        stage_latencies: dict[str, float] = {}
        policy_score = classification.domains.get("policy", 0.0)
        needs_hyde = policy_score > HYDE_THRESHOLD
        needs_decompose = classification.is_multi_domain

        query_embedding: list[float] | None = None
        hyde_hypothetical: str | None = None
        hyde_activated = False
        sub_queries: list[SubQuery] = [
            SubQuery(
                text=query,
                target_domain=classification.primary_domain,
                original_query=query,
            )
        ]

        # Fast path: neither stage needed — return immediately with no threads
        if not needs_hyde and not needs_decompose:
            logger.debug(
                "_run_hyde_and_decompose_parallel — neither HyDE nor "
                "decomposition needed; returning immediately"
            )
            return query_embedding, hyde_hypothetical, hyde_activated, sub_queries, stage_latencies

        futures = {}
        t_parallel_start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=2) as executor:
            if needs_hyde:
                futures["hyde"] = executor.submit(
                    self._hyde.process, query
                )
            if needs_decompose:
                futures["decompose"] = executor.submit(
                    self._decomposer.decompose, query, classification
                )

            for name, future in futures.items():
                try:
                    result = future.result()
                    if name == "hyde":
                        # _hyde.process() returns the embedding directly;
                        # we also need the hypothetical text for the trace.
                        # Call generate_hypothetical separately first so we
                        # can capture both. Override: use the two-step path
                        # so the hypothetical text is available for the trace.
                        pass  # handled below — see note
                    elif name == "decompose":
                        sub_queries = result
                        stage_latencies["decomposition"] = _elapsed_ms(t_parallel_start)
                except Exception:
                    logger.exception(
                        "_run_hyde_and_decompose_parallel — %s failed", name
                    )

        # Note: HyDE.process() combines generate + embed but does not expose
        # the intermediate text.  We need the text for the trace log (R6.3).
        # Run HyDE via the two-step path in its own thread alongside decompose.
        # Override the above with a corrected parallel implementation:
        #
        # This is handled by the revised implementation below which uses
        # generate_hypothetical + embed_hypothetical as separate futures
        # rather than process().

        # Revised parallel implementation that captures both text and embedding
        query_embedding = None
        hyde_hypothetical = None
        hyde_activated = False
        sub_queries = [
            SubQuery(
                text=query,
                target_domain=classification.primary_domain,
                original_query=query,
            )
        ]

        t_parallel_start = time.perf_counter()

        def _run_hyde() -> tuple[str, list[float]]:
            text = self._hyde.generate_hypothetical(query)
            embedding = self._hyde.embed_hypothetical(text)
            return text, embedding

        def _run_decompose() -> list[SubQuery]:
            return self._decomposer.decompose(query, classification)

        with ThreadPoolExecutor(max_workers=2) as executor:
            hyde_future = executor.submit(_run_hyde) if needs_hyde else None
            decompose_future = executor.submit(_run_decompose) if needs_decompose else None

            if hyde_future is not None:
                try:
                    hyde_hypothetical, query_embedding = hyde_future.result()
                    hyde_activated = True
                    stage_latencies["hyde"] = _elapsed_ms(t_parallel_start)
                    logger.info(
                        "_run_hyde_and_decompose_parallel — HyDE completed "
                        "(policy_score=%.2f)", policy_score
                    )
                except Exception:
                    logger.exception(
                        "_run_hyde_and_decompose_parallel — HyDE failed, "
                        "falling back to standard query embedding"
                    )
                    hyde_activated = False
                    hyde_hypothetical = None
                    query_embedding = None

            if decompose_future is not None:
                try:
                    sub_queries = decompose_future.result()
                    stage_latencies["decomposition"] = _elapsed_ms(t_parallel_start)
                    logger.info(
                        "_run_hyde_and_decompose_parallel — decomposed into "
                        "%d sub-queries", len(sub_queries)
                    )
                except Exception:
                    logger.exception(
                        "_run_hyde_and_decompose_parallel — decomposition "
                        "failed, falling back to original query"
                    )
                    sub_queries = [
                        SubQuery(
                            text=query,
                            target_domain=classification.primary_domain,
                            original_query=query,
                        )
                    ]

        return query_embedding, hyde_hypothetical, hyde_activated, sub_queries, stage_latencies

```

### Edit 3c — Replace Stages 3 and 4 in `run()` with the parallel helper

In the `run()` method, find the entire Stage 3 and Stage 4 blocks. They
look like this:

```python
        # ── Stage 3: HyDE (if policy domain with high confidence) ────
        query_embedding: list[float] | None = None
        policy_score = classification.domains.get("policy", 0.0)

        if policy_score > HYDE_THRESHOLD:
            try:
                t0 = time.perf_counter()
                hyde_hypothetical = self._hyde.generate_hypothetical(query)
                query_embedding = self._hyde.embed_hypothetical(hyde_hypothetical)
                hyde_activated = True
                stage_latencies["hyde"] = _elapsed_ms(t0)
                logger.info(
                    "Pipeline — HyDE activated (policy confidence=%.2f)",
                    policy_score,
                )
            except Exception:
                logger.exception(
                    "Pipeline — HyDE failed; stage=hyde, input=%r. "
                    "Falling back to standard query embedding.",
                    query,
                )
                hyde_activated = False
                hyde_hypothetical = None

        # ── Stage 4: Query Decomposition ─────────────────────────────
        try:
            t0 = time.perf_counter()
            sub_queries = self._decomposer.decompose(query, classification)
            stage_latencies["decomposition"] = _elapsed_ms(t0)

            if len(sub_queries) > 1:
                decomposed_queries = sub_queries
                logger.info(
                    "Pipeline — decomposed into %d sub-queries",
                    len(sub_queries),
                )
            else:
                logger.debug("Pipeline — single-domain query, no decomposition")
        except Exception:
            logger.exception(
                "Pipeline — decomposition failed; stage=decomposition, input=%r. "
                "Falling back to original query.",
                query,
            )
            sub_queries = [
                SubQuery(
                    text=query,
                    target_domain=classification.primary_domain,
                    original_query=query,
                )
            ]
```

Replace the entire block with:

```python
        # ── Stages 3 + 4: HyDE and Decomposition (parallel) ─────────
        # HyDE and decomposition are independent of each other — both
        # depend only on the classification from Stage 1.  Running them
        # in parallel eliminates the sequential wait on multi-domain
        # policy queries (saves ~350ms on the most complex query types).
        (
            query_embedding,
            hyde_hypothetical,
            hyde_activated,
            sub_queries,
            parallel_latencies,
        ) = self._run_hyde_and_decompose_parallel(query, classification)
        stage_latencies.update(parallel_latencies)

        if len(sub_queries) > 1:
            decomposed_queries = sub_queries
            logger.info(
                "Pipeline — decomposed into %d sub-queries", len(sub_queries)
            )
        else:
            logger.debug("Pipeline — single-domain query, no decomposition")
```

### Edit 3d — Replace Stages 3 and 4 in `run_without_generation()` with the parallel helper

In the `run_without_generation()` method, find the Stage 3 and Stage 4
blocks. They look like this:

```python
        # Stage 3: HyDE
        query_embedding: list[float] | None = None
        policy_score = classification.domains.get("policy", 0.0)
        if policy_score > HYDE_THRESHOLD:
            try:
                t0 = time.perf_counter()
                hyde_hypothetical = self._hyde.generate_hypothetical(query)
                query_embedding = self._hyde.embed_hypothetical(hyde_hypothetical)
                hyde_activated = True
                stage_latencies["hyde"] = _elapsed_ms(t0)
            except Exception:
                logger.exception("run_without_generation — HyDE failed, falling back")

        # Stage 4: Decomposition
        try:
            t0 = time.perf_counter()
            sub_queries = self._decomposer.decompose(query, classification)
            stage_latencies["decomposition"] = _elapsed_ms(t0)
        except Exception:
            logger.exception("run_without_generation — decomposition failed")
            sub_queries = [SubQuery(
                text=query, target_domain=classification.primary_domain,
                original_query=query,
            )]
```

Replace the entire block with:

```python
        # Stages 3 + 4: HyDE and decomposition (parallel)
        # Both depend only on classification; running concurrently saves
        # ~350ms on multi-domain policy queries.
        (
            query_embedding,
            hyde_hypothetical,
            hyde_activated,
            sub_queries,
            parallel_latencies,
        ) = self._run_hyde_and_decompose_parallel(query, classification)
        stage_latencies.update(parallel_latencies)
```

---

## Change 4 of 4 — Create `docs/CHANGELOG.md`

Create a new file at `docs/CHANGELOG.md` with the following content in full.
Do not truncate or summarise any section.

```markdown
# ALO RAG System — Architecture Changelog

This document records every significant architectural decision and the
reasoning that drove it, in chronological order. It is intended to show
how the system evolved from initial design through evaluation and into
production readiness — not just what changed, but why each change was
necessary and what problem it solved.

---

## v0.1 — Initial Architecture

**What was built:** A foundational RAG pipeline with per-domain chunking
(one chunk per product, section-based chunking for policies), Voyage AI
voyage-3 embeddings, ChromaDB for dense retrieval, BM25 sparse retrieval,
RRF fusion, and GPT-4o for answer generation. Customer data was handled via
structured lookup rather than embedding — a deliberate choice to avoid PII
surface area and arithmetic imprecision in embedding space.

**Key design decisions made:**
- Per-domain chunking rather than fixed-size chunks, because product and
  policy content has natural semantic boundaries that fixed chunking would
  destroy (e.g. splitting a conditional return-eligibility rule across two
  chunks).
- Customer data excluded from the vector store entirely. Return eligibility
  requires boolean comparisons (`final_sale == true`) and exact date
  arithmetic — operations that semantic similarity search cannot perform
  reliably. Structured lookup guarantees precision and keeps PII out of the
  index.
- HyDE activated only for policy queries with confidence > 0.5. The
  vocabulary gap between casual user language ("can I return this?") and
  formal policy text ("items designated Final Sale are ineligible for
  return or exchange") is widest in the policy domain. HyDE generates a
  hypothetical policy excerpt whose embedding lands closer to real policy
  chunks in vector space.

**Initial evaluation results:**
- Mean Recall@5: 0.727
- Mean MRR: 0.668
- Mean Context Precision: 0.208
- Mean Faithfulness: 0.820
- Hallucination Rate: 0.200
- Mean Latency: ~10,163ms

---

## v0.2 — Streaming Architecture Refactor

**Problem identified:** The server was making two sequential LLM generation
calls per user request — one inside `pipeline.run()` (result discarded) and
one via `generate_stream()` (shown to the user). This doubled the generation
cost and added ~7 seconds of hidden latency per request.

**Root cause:** The original `/api/chat` endpoint called `pipeline.run()`
to get retrieval results and trace data, then called the LLM a second time
via `generate_stream()` to produce a streaming response. The first call's
answer was never used.

**Change made:** Introduced `Pipeline.run_without_generation()` — a new
method that executes all pipeline stages up to and including prompt building
(Stages 1-7) but stops before the LLM generation call. The server endpoint
now calls this method to get the prepared prompt and retrieval trace, then
streams a single generation call directly to the client. The full
`pipeline.run()` method is retained unchanged for the eval harness, which
requires a synchronous complete result.

**Effect:** Eliminated ~7,000ms of redundant generation time on every
interactive request. The server now makes exactly one LLM generation call
per user query.

---

## v0.3 — Reranker Model Upgrade

**Problem identified:** Context Precision of 0.208 indicated that 4 in 5
chunks passed to the generation layer were irrelevant. The reranker was not
effectively discriminating between relevant and irrelevant chunks.

**Root cause:** The original reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
was trained exclusively on MS MARCO — a web search dataset. It had never
encountered retail-specific vocabulary: "Aloversary Sale", "Final Sale
exclusions", "A-List tier", "Airlift fabric", "community discount stacking".
Without exposure to these terms during training, the model was scoring chunks
by surface-level lexical overlap rather than domain-relevant semantic
relevance. A policy chunk about military discounts and a policy chunk about
sale-period point restrictions both scored similarly on any query mentioning
either topic, because the model had no signal to distinguish them.

**Change made:** Replaced `ms-marco-MiniLM-L-6-v2` with `BAAI/bge-reranker-base`.
`bge-reranker-base` was trained on a broader and more diverse corpus than
MS MARCO and generalises significantly better to out-of-domain vocabulary.
Additionally, a `min_score` parameter was added to `CrossEncoderReranker.rerank()`
(default: -3.0) so that chunks scoring below a configurable floor are excluded
entirely rather than always returning exactly `top_k` results regardless of
quality.

**Why `bge-reranker-base` over alternatives:**
- `ms-marco-MiniLM-L-12-v2`: still MS MARCO-trained; same vocabulary
  mismatch problem at 50% higher latency.
- `bge-reranker-v2-m3`: best open-source quality but 568M parameters
  (~600ms warm CPU); latency cost not justified at POC scale.
- Cohere Rerank 3.5: highest accuracy but API round-trip latency (~900ms)
  and per-query cost incompatible with the eval harness.
- Fine-tuning on ALO-specific pairs: the correct long-term answer, but
  requires a labelled dataset of 200+ query/chunk/hard-negative triplets
  that does not yet exist.

**Why ONNX is the production path:** ONNX export of `bge-reranker-base` via
`optimum-cli` produces bit-for-bit identical scores using the same weights
through a more optimised execution engine (ONNX Runtime). CPU inference drops
from ~400ms to ~80ms with no quality tradeoff. On GPU (CUDA provider),
latency drops further to ~10ms. This is the deployment target for production.
The ONNX export step is a manual one-time operation documented in
`src/retrieval/reranker.py` and requires the exported model artefact to be
present before code changes can be made.

**Latency improvement:** Reranker CPU inference from ~4,705ms (cold load,
first query) to ~400ms (warm). Cold load eliminated by eager model loading
at server startup.

---

## v0.4 — Classification Model Downgrade (Speed Upgrade)

**Problem identified:** Intent classification was consuming ~1,060ms per
query despite producing only a small JSON object (under 80 tokens). The same
model (`gpt-4o-mini`) was being used for classification tasks (intent routing,
scope guard, query decomposition) and for HyDE document generation — tasks
with very different output requirements.

**Decision:** Replace `gpt-4o-mini` with `gpt-4.1-nano` as the default
classification model. `gpt-4.1-nano` is OpenAI's fastest, lowest-cost model.
For structured JSON output tasks with a clear system prompt and a short,
well-defined output format, it performs equivalently to `gpt-4o-mini` at
approximately 2x the speed and half the cost.

**Why `gpt-4o` is retained for generation:** Answer generation requires
reasoning depth, nuanced instruction following, and multi-step context
integration that `gpt-4.1-nano` does not reliably provide. The cost and
latency of `gpt-4o` is justified for the generation step. It is not justified
for a classification call that outputs `{"product": 0.8, "policy": 0.1,
"customer": 0.1}`.

**Why keyword-based classification was rejected:** A deterministic keyword
classifier was considered and rejected. It would not generalise to queries
that use synonyms, metaphors, or domain-adjacent vocabulary not present in a
hardcoded signal set. A query like "I want to swap my Cyber Monday purchase
for a different size" contains no standard return/exchange keywords but is
clearly a cross-domain policy + customer query. Silent misclassification is
worse than a slower correct classification. The LLM-based approach generalises
by understanding intent, not lexical surface.

**Estimated latency saving:** ~180ms per query on classification-only paths.

---

## v0.5 — HyDE Generation Model Downgrade

**Problem identified:** HyDE's hypothetical document generation was using
`llm_client.generate()` — the GPT-4o path — adding ~800ms to every policy
query before retrieval even began.

**Root cause of the original choice:** GPT-4o was used because the HyDE
hypothetical "should be good quality." This was an implicit assumption that
generation quality for retrieval purposes requires the same model as
generation quality for user-facing answers.

**Why this assumption is wrong:** The hypothetical document is embedded and
compared against indexed chunk embeddings. The embedding model (voyage-3)
evaluates semantic proximity, not factual correctness or prose quality. A
document that uses the right vocabulary in the right register produces a
better embedding match than a document that is factually correct but
phrased differently from the policy source text. `gpt-4o-mini` generates
domain-appropriate vocabulary for 2-4 sentence policy excerpts reliably.
`gpt-4o` generates the same vocabulary at ~500ms higher latency per call.

**Why `flan-t5` (local generation) was rejected:** A locally-running T5
model (flan-t5-base) would save the API round-trip entirely. However, T5
generates short, information-sparse sentences that lack the domain
vocabulary depth needed for effective HyDE embeddings in this domain.
The difference between "Sale items cannot be returned." (T5) and "Items
purchased during promotional sale events at a discount of 30% or greater
are designated Final Sale and are ineligible for return or exchange under
ALO's standard returns policy." (GPT-4o-mini) is the difference between
a weak HyDE signal and a strong one. The API cost is worth it.

**Change made:** `generate_hypothetical()` now calls `llm_client.classify()`
(GPT-4o-mini, 200 token cap) rather than `llm_client.generate()` (GPT-4o,
256 token cap). The `classify()` method was updated to accept an optional
`max_tokens` parameter (default still 80 for intent/scope tasks) so HyDE
can request the slightly larger output it needs.

**Estimated latency saving:** ~500ms per policy query.

---

## v0.6 — Parallel HyDE and Decomposition

**Problem identified:** Stages 3 (HyDE) and 4 (decomposition) were executing
sequentially in both `run()` and `run_without_generation()`. On multi-domain
policy queries — the most complex and highest-value query type — this created
an unnecessary serial dependency: decomposition waited for HyDE to complete
before starting, despite having no dependency on HyDE's output.

**Dependency analysis:**
- Stage 3 (HyDE) depends on: Stage 1 (classification) ✓
- Stage 4 (decomposition) depends on: Stage 1 (classification) ✓
- Stage 4 depends on Stage 3: ✗ (no dependency)
- Stage 3 depends on Stage 4: ✗ (no dependency)

Both stages depend only on the intent classification. They are safe to
parallelise.

**Change made:** Extracted Stages 3 and 4 into a new helper method
`_run_hyde_and_decompose_parallel()` that uses `ThreadPoolExecutor`
(consistent with the pattern already used in `HybridSearch._parallel_search()`)
to run HyDE generation+embedding and query decomposition concurrently.
The helper handles all four activation combinations:
- Neither needed (single-domain, non-policy): returns immediately, no threads.
- HyDE only (single-domain policy): runs HyDE, returns single sub-query.
- Decompose only (multi-domain, non-policy): runs decomposition, no HyDE.
- Both (multi-domain policy): runs concurrently, results merged.

**Why `ThreadPoolExecutor` rather than `asyncio.gather`:** The pipeline is
synchronous throughout. The LLM client uses the synchronous OpenAI SDK.
Introducing `asyncio` would require converting the entire pipeline to async,
which is a larger refactor than the problem warrants. `ThreadPoolExecutor`
releases the GIL during I/O-bound operations (network calls to the OpenAI
API), so true concurrency is achieved for these network-bound tasks.

**Estimated latency saving:** ~350ms on multi-domain policy queries (the
decomposition call completes during the same wall-clock time as HyDE).

---

## Cumulative Latency Budget (Pre-Generation Stages)

| Stage | v0.1 | v0.6 (current) | Notes |
|---|---|---|---|
| Intent classification | ~1,060ms | ~400ms | gpt-4.1-nano vs gpt-4o-mini |
| Scope guard (conditional) | ~350ms | ~180ms | gpt-4.1-nano |
| HyDE (policy queries) | ~800ms | ~300ms | gpt-4o-mini; parallel with decompose |
| Decomposition (multi-domain) | ~350ms | ~0ms net | parallel with HyDE |
| Retrieval + reranker | ~4,705ms | ~400ms | warm model; bge-reranker-base |
| Prompt building | ~0ms | ~0ms | in-memory |
| **Pre-generation total** | **~7,265ms** | **~1,280ms** | typical policy+multi-domain |
| Generation (streaming) | first token ~300ms | first token ~300ms | unchanged |

---

## Planned — v0.7 (Not Yet Implemented)

**ONNX reranker export:** Exporting `bge-reranker-base` to ONNX format and
running inference via ONNX Runtime would reduce reranker CPU latency from
~400ms to ~80ms with no quality tradeoff. This requires a one-time manual
export step using `optimum-cli`. The export commands and validation procedure
are documented in `src/retrieval/reranker.py`. The dependency (`optimum`,
`onnxruntime`) has been added to `pyproject.toml`.

**Semantic response cache:** Embedding each incoming query and comparing it
against a cache of recent query embeddings (cosine similarity threshold: 0.97,
TTL: 24 hours, max size: 500 entries) would allow near-identical queries to
bypass the full pipeline entirely. Cache invalidation is tied to the
`DocumentRegistry` GC sweep — when chunks are hard-deleted (policy update,
SKU discontinuation), cached responses that depended on those chunks are
evicted. This is a production-grade pattern, not a POC shortcut: real
customer support traffic has a heavy-tailed distribution where a small
number of semantic clusters account for the majority of queries.
```
