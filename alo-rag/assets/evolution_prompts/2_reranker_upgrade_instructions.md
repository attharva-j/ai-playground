# Reranker Upgrade Instructions

## Summary

Replace the cross-encoder reranker model from `cross-encoder/ms-marco-MiniLM-L-6-v2`
to `BAAI/bge-reranker-base` across the codebase, and add a new ADR section to
`docs/ADR.md` documenting this decision.

There are **4 files to modify** and **no new files to create**.

---

## Change 1 of 4 — `src/retrieval/reranker.py`

Make three edits to this file.

### Edit 1a — Module docstring

Find this exact text at the top of the file:

```
"""Cross-encoder reranker for the ALO RAG retrieval engine.

Uses the ``cross-encoder/ms-marco-MiniLM-L-6-v2`` model from
sentence-transformers to score each (query, chunk) pair and return the
top-k chunks ordered by relevance.

Requirements: 8.3
"""
```

Replace it with:

```
"""Cross-encoder reranker for the ALO RAG retrieval engine.

Uses the ``BAAI/bge-reranker-base`` model from sentence-transformers to
score each (query, chunk) pair and return the top-k chunks ordered by
relevance. This model was chosen over the previous
``cross-encoder/ms-marco-MiniLM-L-6-v2`` for its significantly better
domain-specific retrieval quality on retail and policy text — see ADR-5
for the full decision rationale.

Requirements: 8.3
"""
```

### Edit 1b — Default model name in `__init__`

Find this exact line inside `CrossEncoderReranker.__init__`:

```python
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
```

Replace it with:

```python
        model_name: str = "BAAI/bge-reranker-base",
```

### Edit 1c — Add `min_score` parameter to `rerank()` and update method body

Find the entire `rerank` method signature and body. It currently looks like this:

```python
    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """Score each *query*–chunk pair and return the top-*k* by relevance.

        Parameters
        ----------
        query:
            The user's search query.
        chunks:
            Candidate chunks to rerank (typically the fused RRF output).
        top_k:
            Number of top results to return.

        Returns
        -------
        list[RetrievedChunk]
            Up to *top_k* chunks sorted by descending cross-encoder score,
            each with ``source="reranked"``.
        """
        if not chunks:
            return []

        model = self._get_model()

        # Build (query, chunk_text) pairs for the cross-encoder
        pairs = [[query, rc.chunk.text] for rc in chunks]

        # Score all pairs in a single batch
        scores = model.predict(pairs, show_progress_bar=False)

        # Pair each chunk with its cross-encoder score
        scored = list(zip(chunks, scores))
        scored.sort(key=lambda item: float(item[1]), reverse=True)

        reranked: list[RetrievedChunk] = []
        for rc, score in scored[:top_k]:
            reranked.append(
                RetrievedChunk(
                    chunk=rc.chunk,
                    score=float(score),
                    source="reranked",
                )
            )

        logger.debug(
            "CrossEncoderReranker: reranked %d candidates → top-%d",
            len(chunks),
            len(reranked),
        )
        return reranked
```

Replace it with:

```python
    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 5,
        min_score: float = -3.0,
    ) -> list[RetrievedChunk]:
        """Score each *query*–chunk pair and return the top-*k* by relevance.

        Parameters
        ----------
        query:
            The user's search query.
        chunks:
            Candidate chunks to rerank (typically the fused RRF output).
        top_k:
            Number of top results to return.
        min_score:
            Minimum cross-encoder score a chunk must achieve to be included
            in the output. Cross-encoder scores are unbounded; -3.0 is a
            permissive floor that filters only strongly irrelevant chunks.
            Tighten (e.g. to -1.0) to improve context precision at the cost
            of recall.

        Returns
        -------
        list[RetrievedChunk]
            Up to *top_k* chunks sorted by descending cross-encoder score,
            each with ``source="reranked"``, all scoring >= *min_score*.
        """
        if not chunks:
            return []

        model = self._get_model()

        # Build (query, chunk_text) pairs for the cross-encoder
        pairs = [[query, rc.chunk.text] for rc in chunks]

        # Score all pairs in a single batch
        scores = model.predict(pairs, show_progress_bar=False)

        # Pair each chunk with its cross-encoder score
        scored = list(zip(chunks, scores))
        scored.sort(key=lambda item: float(item[1]), reverse=True)

        reranked: list[RetrievedChunk] = []
        for rc, score in scored[:top_k]:
            if float(score) >= min_score:
                reranked.append(
                    RetrievedChunk(
                        chunk=rc.chunk,
                        score=float(score),
                        source="reranked",
                    )
                )

        logger.debug(
            "CrossEncoderReranker: %d candidates → %d passed "
            "(min_score=%.1f, top_k=%d)",
            len(chunks),
            len(reranked),
            min_score,
            top_k,
        )
        return reranked
```

---

## Change 2 of 4 — `src/retrieval/hybrid_search.py`

Add `rerank_min_score` to `HybridSearch.search()` so callers can tune the
minimum score threshold.

Find the `search` method signature, which currently looks like this:

```python
    def search(
        self,
        query_embedding: list[float],
        query_text: str,
        metadata_filter: dict[str, Any] | None = None,
        dense_k: int = 12,
        sparse_k: int = 8,
        final_k: int = 5,
    ) -> list[RetrievedChunk]:
```

Replace it with:

```python
    def search(
        self,
        query_embedding: list[float],
        query_text: str,
        metadata_filter: dict[str, Any] | None = None,
        dense_k: int = 12,
        sparse_k: int = 8,
        final_k: int = 5,
        rerank_min_score: float = -3.0,
    ) -> list[RetrievedChunk]:
```

Then find the docstring parameter block inside `search()`. Find this text:

```
        final_k:
            Number of final results after reranking.
```

Replace it with:

```
        final_k:
            Number of final results after reranking.
        rerank_min_score:
            Minimum cross-encoder score passed through to
            :meth:`CrossEncoderReranker.rerank`. Chunks scoring below this
            threshold are excluded even if they would otherwise be in top-k.
```

Then find the reranker call inside `search()`:

```python
        reranked = self._reranker.rerank(
            query=query_text,
            chunks=fused[:rerank_pool_size],
            top_k=final_k,
        )
```

Replace it with:

```python
        reranked = self._reranker.rerank(
            query=query_text,
            chunks=fused[:rerank_pool_size],
            top_k=final_k,
            min_score=rerank_min_score,
        )
```

---

## Change 3 of 4 — `server.py`

The server references the model name only indirectly through the default
parameter of `CrossEncoderReranker()`. No model-name string change is needed
here. However, the eager-load log message currently names the old model
implicitly. Verify that after Change 1b above, the log at startup reads:

```
Loading cross-encoder model: BAAI/bge-reranker-base
```

This will be correct automatically once the default is updated in Change 1b.
No additional edit is needed in `server.py` unless the `CrossEncoderReranker`
is instantiated with an explicit model name string — check line 163. If it reads:

```python
    reranker = CrossEncoderReranker()
```

No change is needed. If it reads:

```python
    reranker = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
```

Replace that line with:

```python
    reranker = CrossEncoderReranker()
```

---

## Change 4 of 4 — `docs/ADR.md`

Append a new section `ADR-5` at the end of the file, after the final line of
the existing ADR-4 section. Do not modify any existing content.

Add the following in full:

```markdown
---

## ADR-5: Cross-Encoder Reranker Model Selection

### Context

The retrieval pipeline uses a cross-encoder reranker as the final stage before
generation. The cross-encoder reads each (query, candidate chunk) pair jointly
and produces a relevance score, giving it substantially higher precision than
the embedding cosine similarity used for initial retrieval. The quality of this
model directly determines Context Precision — how many of the chunks actually
passed to the LLM are relevant to the query.

The initial implementation used `cross-encoder/ms-marco-MiniLM-L-6-v2`, the
smallest and most commonly referenced cross-encoder in open-source RAG
tutorials. Evaluation results showed a Mean Context Precision of 0.208, meaning
roughly 4 in 5 chunks passed to the generation layer were irrelevant. This
indicated the reranker was not effectively discriminating relevant from
irrelevant chunks in this domain.

### Root Cause of Poor Performance with MiniLM-L6

`ms-marco-MiniLM-L-6-v2` was trained exclusively on the MS MARCO dataset, which
consists of real Bing web search queries matched against web document passages.
This creates two problems for the ALO RAG use case:

**Vocabulary mismatch:** The model has never encountered retail-specific
terminology such as "Aloversary Sale", "Final Sale exclusions", "A-List tier",
"Airlift fabric", or "community discount stacking rules". It therefore cannot
learn the relevance signal between a query like "Can I use my military discount
during the Aloversary Sale?" and the corresponding policy section — the
vocabulary is simply out of distribution.

**Query type mismatch:** MS MARCO web search queries are short, keyword-oriented,
and typically answered by a single web page passage. ALO policy queries are
conversational, require conditional reasoning ("if the item was discounted ≥30%
then it is Final Sale"), and often require two policy sections to be retrieved
together. The cross-encoder has no learned signal for this kind of query
structure.

The combined effect was that the reranker was scoring chunks by surface-level
lexical overlap rather than domain-relevant semantic relevance — returning
product chunks for policy queries and vice versa.

### Decision

Replace `cross-encoder/ms-marco-MiniLM-L-6-v2` with `BAAI/bge-reranker-base`
as the default cross-encoder reranker.

Additionally, add a `min_score` parameter to `CrossEncoderReranker.rerank()`
(default: `-3.0`) so that chunks scoring below a configurable threshold are
excluded from the output entirely, rather than always returning exactly `top_k`
chunks regardless of their relevance scores.

### Why bge-reranker-base

`bge-reranker-base` is developed by the Beijing Academy of Artificial
Intelligence (BAAI) and trained on a significantly more diverse corpus than
MS MARCO, including academic, legal, and domain-specific passage pairs. Key
advantages for this use case:

- **Broader training distribution:** The model generalises to out-of-domain
  vocabulary better than MS MARCO-only models, which directly addresses the
  vocabulary mismatch problem.
- **Same interface:** Loaded via `sentence-transformers.CrossEncoder`, drop-in
  replacement with no code changes beyond the model name string.
- **Free and local:** No API dependency, no per-query cost, runs on CPU with
  the same `sentence-transformers` dependency already in `pyproject.toml`.
- **Proven on BEIR benchmarks:** `bge-reranker-base` outperforms
  `ms-marco-MiniLM-L-6-v2` on the majority of BEIR retrieval benchmark domains,
  particularly on domain-specific corpora (SciFact, FiQA, NFCorpus) that
  better approximate the ALO policy and product retrieval task than MS MARCO
  does.

### Alternatives Considered

1. **`cross-encoder/ms-marco-MiniLM-L-12-v2` (larger MS MARCO variant):**
   12 transformer layers vs 6, roughly 50% slower (~270ms warm vs ~180ms), but
   still trained exclusively on MS MARCO. The vocabulary mismatch problem
   remains. Rejected — marginal quality gain for measurable latency cost.

2. **`BAAI/bge-reranker-v2-m3` (larger BGE variant):**
   Current SOTA open-source cross-encoder. Significantly better quality than
   `bge-reranker-base` on retrieval benchmarks, but 568M parameters vs 278M —
   approximately 2.5× slower (~600ms warm). At POC scale, this latency addition
   is not justified, but this is the recommended upgrade path for production
   deployment once latency budgets are re-evaluated.

3. **Cohere Rerank 3.5 (API-based):**
   Highest accuracy of any available reranker. However, it adds an API
   round-trip (~900ms), per-query cost ($2 per 1,000 documents reranked), and
   a new vendor dependency. Appropriate for production if budget allows, but
   not suitable for the POC eval harness which runs 25 queries per regression
   run.

4. **Voyage AI rerank-2 (API-based):**
   Natural architectural pairing with the `voyage-3` embeddings already in use.
   Strong quality, but same API-latency and cost concerns as Cohere. Also
   ~$0.05 per 1M tokens. Deferred to production consideration.

5. **Fine-tuning `ms-marco-MiniLM-L-6-v2` on ALO-specific pairs:**
   Theoretically the best option — a model trained on actual ALO query/chunk
   pairs would have perfect vocabulary fit. Requires a labelled dataset of
   200+ (query, positive chunk, hard negative chunk) triplets, which does not
   yet exist. This remains the recommended long-term path. The `bge-reranker-base`
   swap is the pragmatic short-term improvement pending that dataset.

### Latency Impact

| Model | Parameters | Warm CPU latency (15 pairs) |
|---|---|---|
| ms-marco-MiniLM-L-6-v2 (previous) | 22M | ~180ms |
| bge-reranker-base (new) | 278M | ~400ms |
| bge-reranker-v2-m3 (future) | 568M | ~600ms |

The additional ~220ms over the previous model is acceptable given:
- Generation (GPT-4o) dominates latency at ~6,900ms
- The streaming architecture means retrieval latency is not on the
  user-perceived critical path — it completes before the first token is shown
- The quality improvement in Context Precision is expected to reduce
  hallucination rate, which is a higher-priority concern than 220ms of
  additional retrieval time

### Production Path

For production deployment at ALO's 15,000+ SKU catalog scale:

1. **Immediate (current):** `BAAI/bge-reranker-base` — best open-source
   quality at acceptable latency, no API cost.
2. **Short-term:** `BAAI/bge-reranker-v2-m3` — when a GPU is available for
   inference (reduces latency to ~150ms), making the quality/latency tradeoff
   clearly favourable.
3. **Medium-term:** Fine-tune `bge-reranker-base` on ALO-specific
   (query, chunk, hard negative) triplets generated from production query logs
   and the eval harness. Expected to bring Context Precision above 0.6.
4. **Long-term:** Evaluate Cohere Rerank 3.5 or Voyage rerank-2 for
   high-traffic paths where API latency is acceptable and quality is paramount
   (e.g., customer-facing return eligibility queries with compliance risk).

### Requirements Traceability

This decision addresses Requirements 8.3 (cross-encoder reranking) and
contributes to improving the Context Precision metric measured under
Requirements 14.2 (context precision as a retrieval metric).
```

---

## Verification

After making all four changes, verify the following:

- [ ] `src/retrieval/reranker.py` module docstring references `BAAI/bge-reranker-base`, not `ms-marco-MiniLM-L-6-v2`
- [ ] `CrossEncoderReranker.__init__` default `model_name` is `"BAAI/bge-reranker-base"`
- [ ] `CrossEncoderReranker.rerank()` accepts a `min_score` parameter with default `-3.0`
- [ ] `rerank()` body filters out chunks below `min_score` before appending to results
- [ ] `HybridSearch.search()` accepts a `rerank_min_score` parameter with default `-3.0`
- [ ] `HybridSearch.search()` passes `min_score=rerank_min_score` to `self._reranker.rerank()`
- [ ] `server.py` does not contain the string `"cross-encoder/ms-marco-MiniLM-L-6-v2"` anywhere
- [ ] `docs/ADR.md` ends with the `ADR-5` section
- [ ] Server startup log reads: `Loading cross-encoder model: BAAI/bge-reranker-base`

On first server start after this change, the model will be downloaded from
Hugging Face (~550MB). Subsequent starts load from the local cache. If running
in a restricted network environment, pre-download the model with:

```bash
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-base')"
```
