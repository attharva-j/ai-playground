**Fix 1 — Context Precision (0.208 → target ≥0.45):**
- Added min_score parameter to CrossEncoderReranker.rerank() — chunks scoring below the threshold are dropped even if fewer than top_k remain. This eliminates low-relevance noise.
- Added rerank_min_score parameter to HybridSearch.search() (default -2.0, which is permissive — you can tighten it).
- Changed pipeline to use adaptive final_k: single-domain queries get final_k=3 (tighter, less noise), multi-domain sub-queries get final_k=4 each so both domains are represented.

**Fix 2 — Latency (10,163ms → target ≤3,000ms):**

- Interactive chat server already uses _NoOpGuardrail (skips the ~3s verification call).
- Eval harness now uses a separate LLMClient(model="gpt-4o-mini") for the faithfulness guardrail — GPT-4o-mini is ~3x faster and ~10x cheaper than GPT-4o for structured verification tasks.
- Reduced max_tokens on the verification call from 2048 to 1024.

**Fix 3 — Hallucination Rate (0.120 → target ≤0.05):**

- Multi-domain queries now get final_k=4 per sub-query (up from the shared 5 total), so cross-domain queries like "Final Sale + points redemption" get 4 chunks from each domain instead of 5 total split unevenly.
- This ensures both the loyalty and returns policy chunks make it into the final context for the hard cross-domain queries.