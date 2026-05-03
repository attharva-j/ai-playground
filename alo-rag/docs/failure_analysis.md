# Failure Analysis — ALO RAG System

## Methodology

The three worst-performing queries were identified by sorting per-query
results by a combined score: `0.4 * recall_at_5 + 0.3 * faithfulness + 0.3 * answer_relevance`.
Queries are analysed below with root-cause diagnosis and specific remediations.

---

## TQ-008 — "What is the status of my order?"

**Scores:** Recall@5=0.00, MRR=0.00, Faithfulness=1.00, Relevance=0.80

**Root cause:** This is a customer-context query submitted without a `customer_id`.
The intent router correctly identifies the customer domain (high confidence), but
because no customer profile is selected in the session, `CustomerContextInjector`
returns `None`. The retriever has no signal for which order to look up and falls
back to product/policy chunks, none of which are relevant to an order status query.
The model produces a generic response ("I don't have access to your order details")
rather than a specific order status — which is technically correct but scores zero
on retrieval because no relevant chunks are surfaced.

**Why faithfulness is 1.00 despite retrieval failure:** The model correctly
acknowledged it couldn't answer rather than hallucinating, so the faithfulness
judge found no unsupported claims. This is the system behaving correctly — the
failure is in the eval setup (query sent without required customer context), not
the pipeline logic.

**Remediation:** Add a pre-retrieval guard in the pipeline: if intent classification
scores `customer > 0.3` and `customer_id is None`, short-circuit immediately with a
clarifying response. Do not attempt retrieval. Update the test query to include the
correct `customer_id` so the eval measures actual retrieval performance.

---

## TQ-015 — "What is the status of my return for the Vapor Crewneck?"

**Scores:** Recall@5=0.00, MRR=0.00, Faithfulness=0.00, Relevance=0.80, Hallucination=Y

**Root cause:** Same missing-customer-id root cause as TQ-008, but with a worse
outcome. The Vapor Crewneck maps to SKU `M6801R-BLK` and appears in Ethan Brooks's
order history (CUST-10177) with status "Return Requested — Pending." Without the
customer profile injected, the model has no ground truth for the return status and
hallucinated a specific status rather than acknowledging it couldn't know.

The faithfulness guardrail failed to catch this. It checks "are claims supported by
the retrieved context?" — but the retrieved context contained only irrelevant
product/policy chunks. The guardrail verified claims against the wrong context,
found them plausible-sounding relative to generic return policy text, and passed
the answer through.

**Why this is a guardrail design gap:** The guardrail should detect the case where
retrieved context is empty or entirely off-domain relative to the query before
attempting claim verification. A claim about a specific order return status cannot
be verified against policy text.

**Remediation:**
1. Same customer-id guard as TQ-008 — this query requires customer context.
2. Add a null-retrieval handler: if no chunks are retrieved that match the query's
   primary domain, return "I don't have enough information to answer that" rather
   than proceeding to generation.
3. Update the test query with `customer_id: "CUST-10177"`.

---

## TQ-018 — "Can I use my military discount during the Aloversary Sale?"

**Scores:** Recall@5=0.00, MRR=0.00, Faithfulness=0.00, Relevance=0.80, Hallucination=Y

**Root cause:** This query requires joining information from two separate sections
of `alo_access_loyalty_program.md`:

1. **Section on community discounts** — covers the military discount (15% for
   verified military members, applied via the GovX portal)
2. **Section on point redemption restrictions** — covers the rule that points
   cannot be redeemed during sale periods, and by extension that sale-period
   pricing takes precedence over stackable discounts

These two sections were chunked independently. Neither section alone matches the
full query ("military discount" + "Aloversary Sale") with high enough confidence
to make the top-5. The BM25 sparse index splits its score between them, and the
cross-encoder evaluates each chunk in isolation — without the other section present
as context, neither chunk looks like a complete answer to the question.

HyDE should have helped here (the query is policy-domain with high confidence), but
the generated hypothetical may not have contained both "military" and "Aloversary"
vocabulary together, limiting its benefit.

**Remediation:**
1. Add overlapping metadata tags to both relevant chunks at ingestion time:
   `sale_restriction: true` on the sale-period restriction section, and
   `community_discount: true` on the military discount section. Use metadata
   post-filtering to boost both when either tag is detected in the query.
2. Verify HyDE is activating for this query by inspecting `trace.hyde_activated`.
   If it is not (policy confidence may be just below 0.5), lower `HYDE_THRESHOLD`
   to 0.4 or add explicit keywords ("discount", "policy", "eligible") to the
   policy-domain classification prompt.
3. Consider a "companion chunk" strategy for the loyalty document: when the
   military discount section is retrieved, always also retrieve the sale-period
   restriction section as a paired result, since they are logically interdependent.
