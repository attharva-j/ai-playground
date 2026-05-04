"""CLI entry point for running the ALO RAG evaluation harness.

Usage (from the alo-rag/ directory):
    python -m src.eval [--data-dir DATA_DIR] [--queries QUERIES_PATH] [-v]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
import json

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the ALO RAG evaluation harness",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Root data directory (default: data)",
    )
    parser.add_argument(
        "--queries",
        type=Path,
        default=Path("evals/test_queries.json"),
        help="Path to test queries JSON (default: evals/test_queries.json)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    parser.add_argument(
        "--mode",
        choices=["smoke", "full"],
        default="full",
        help="Eval mode: 'smoke' runs 8 representative queries, 'full' runs all (default: full)",
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save results as the regression baseline",
    )
    parser.add_argument(
        "--compare-baseline",
        action="store_true",
        help="Compare results against stored baseline",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write JSON eval results",
    )
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # Load .env from workspace root
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")
    except ImportError:
        pass

    # --- Build the pipeline (same as server.py) ---
    from src.generation.customer_context import CustomerContextInjector
    from src.generation.llm_client import LLMClient
    from src.generation.prompt_builder import PromptBuilder
    from src.ingestion.chunkers import PolicyChunker, ProductChunker
    from src.ingestion.embedders import EmbeddingService
    from src.ingestion.index_builder import BM25Builder, VectorStore
    from src.ingestion.loaders import PolicyLoader, ProductLoader
    from src.pipeline import Pipeline
    from src.query.decomposer import QueryDecomposer
    from src.query.hyde import HyDEModule
    from src.query.intent_router import IntentRouter
    from src.query.scope_guard import ScopeGuard
    from src.retrieval.fusion import RRFFuser
    from src.retrieval.hybrid_search import HybridSearch
    from src.retrieval.reranker import CrossEncoderReranker

    data_dir = args.data_dir
    products_path = data_dir / "products" / "alo_product_catalog.json"
    policies_path = data_dir / "policies"
    customers_path = data_dir / "customers" / "customer_order_history.json"

    logger.info("Building pipeline...")

    embedding_service = EmbeddingService()
    llm_client = LLMClient()

    product_docs = ProductLoader().load(products_path)
    policy_docs = PolicyLoader().load(policies_path)

    product_chunks, _ = ProductChunker().chunk(product_docs)
    policy_chunks = PolicyChunker().chunk(policy_docs)
    all_chunks = product_chunks + policy_chunks

    texts = [c.text for c in all_chunks]
    embeddings = embedding_service.embed(texts)

    vector_store = VectorStore(collection_name="alo_rag_eval")
    vector_store.add(all_chunks, embeddings)
    bm25_index = BM25Builder().build(all_chunks)

    # Use the same no-op guardrail as the demo server so the pipeline
    # produces identical answers.  Faithfulness is still measured as a
    # metric via GenerationMetrics.faithfulness() — the guardrail in the
    # pipeline would alter the answer (reject / regenerate) before the
    # metric evaluator sees it, creating a functional divergence between
    # the eval harness and the live demo.
    from src.models import FaithfulnessResult as _FR

    class _NoOpGuardrail:
        def verify(self, answer: str, context_chunks: list, query: str = "") -> _FR:
            return _FR(
                score=1.0,
                claims=[],
                unsupported_claims=[],
                regeneration_triggered=False,
                regenerated_answer=None,
            )

    pipeline = Pipeline(
        intent_router=IntentRouter(llm_client),
        hyde=HyDEModule(llm_client, embedding_service),
        decomposer=QueryDecomposer(llm_client),
        scope_guard=ScopeGuard(llm_client),
        retrieval=HybridSearch(
            vector_store=vector_store,
            bm25_index=bm25_index,
            rrf_fuser=RRFFuser(k=60),
            reranker=CrossEncoderReranker(),
        ),
        prompt_builder=PromptBuilder(),
        llm_client=llm_client,
        guardrail=_NoOpGuardrail(),
        customer_injector=CustomerContextInjector(data_path=customers_path),
        embedding_service=embedding_service,
    )

    # --- Load queries and run ---
    from src.eval.harness import EvalHarness, load_test_queries

    logger.info("Loading test queries from %s", args.queries)
    test_queries = load_test_queries(args.queries)

    if args.mode == "smoke":
        # Select representative queries: 1 per domain + 1 cross-domain + 1 hard + 1 customer
        smoke_ids = set()
        for domain in ["product", "policy", "customer", "cross-domain"]:
            for tq in test_queries:
                if tq.domain == domain and tq.query_id not in smoke_ids:
                    smoke_ids.add(tq.query_id)
                    break
        # Add one hard query
        for tq in test_queries:
            if tq.difficulty == "hard" and tq.query_id not in smoke_ids:
                smoke_ids.add(tq.query_id)
                break
        # Add one customer-context query
        for tq in test_queries:
            if tq.customer_id and tq.query_id not in smoke_ids:
                smoke_ids.add(tq.query_id)
                break
        # Add one known difficult query (TQ-018 or similar)
        for tq in test_queries:
            if tq.query_id == "TQ-018" and tq.query_id not in smoke_ids:
                smoke_ids.add(tq.query_id)
                break
        # Add one more for coverage
        for tq in test_queries:
            if tq.query_id not in smoke_ids:
                smoke_ids.add(tq.query_id)
                break

        test_queries = [tq for tq in test_queries if tq.query_id in smoke_ids]
        logger.info("Smoke mode: selected %d queries: %s",
                     len(test_queries), [tq.query_id for tq in test_queries])

    harness = EvalHarness(pipeline=pipeline, test_queries=test_queries)

    logger.info("Running evaluation (%d queries)...", len(test_queries))
    results = harness.run()
    aggregate = harness.compute_aggregate_metrics(results)

    # --- Print results ---
    print("\n" + "=" * 70)
    print("  ALO RAG Evaluation Results")
    print("=" * 70)
    print(f"  Queries evaluated:      {aggregate.total_queries}")
    print(f"  Mean Recall@5:          {aggregate.mean_recall_at_5:.3f}")
    print(f"  Mean MRR:               {aggregate.mean_mrr:.3f}")
    print(f"  Mean Context Precision: {aggregate.mean_context_precision:.3f}")
    print(f"  Mean Faithfulness:      {aggregate.mean_faithfulness:.3f}")
    print(f"  Mean Answer Relevance:  {aggregate.mean_answer_relevance:.3f}")
    print(f"  Hallucination Rate:     {aggregate.hallucination_rate:.3f}")
    print(f"  Mean Latency:           {aggregate.mean_latency_ms:.0f} ms")
    print(f"  Behavior Success Rate: {aggregate.behavior_success_rate:.3f}")
    print("-" * 70)

    if aggregate.queries_by_difficulty:
        print("  By difficulty:")
        for diff, count in sorted(aggregate.queries_by_difficulty.items()):
            print(f"    {diff}: {count}")

    if aggregate.queries_by_domain:
        print("  By domain:")
        for domain, count in sorted(aggregate.queries_by_domain.items()):
            print(f"    {domain}: {count}")

    # Latency percentiles
    latencies = sorted([r.latency_ms for r in results])
    if latencies:
        p50_idx = len(latencies) // 2
        p95_idx = min(int(len(latencies) * 0.95), len(latencies) - 1)
        print(f"  p50 Latency:            {latencies[p50_idx]:.0f} ms")
        print(f"  p95 Latency:            {latencies[p95_idx]:.0f} ms")

    print("-" * 70)
    print("  Per-query results:")
    for r in results:
        print(
            f"    {r.query_id:8s}  R@5={r.recall_at_5:.2f}  "
            f"MRR={r.mrr:.2f}  Faith={r.faithfulness:.2f}  "
            f"Rel={r.answer_relevance:.2f}  "
            f"Halluc={'Y' if r.has_hallucination else 'N'}  "
            f"{r.latency_ms:.0f}ms"
        )
    print("=" * 70 + "\n")

    # --- Failure analysis ---
    from src.eval.failure_analysis import FailureAnalyzer

    query_lookup = {tq.query_id: tq.query for tq in test_queries}
    analyzer = FailureAnalyzer(query_lookup=query_lookup)
    failures = analyzer.analyze(results)

    if failures:
        print("Top failure analysis:")
        for f in failures:
            print(f"  {f.query_id}: score={f.combined_score:.3f}")
            print(f"    Query: {f.query}")
            for issue in f.retrieval_issues:
                print(f"    [retrieval] {issue}")
            for issue in f.generation_issues:
                print(f"    [generation] {issue}")
            for rec in f.recommendations:
                print(f"    → {rec}")
            print()

    from dataclasses import asdict
    from datetime import datetime, timezone
    from src.eval.regression import RegressionHarness

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "aggregate": asdict(aggregate),
        "results": [asdict(r) for r in results],
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Saved eval results to {args.output}")

    regression = RegressionHarness()

    if args.save_baseline:
        regression.save_baseline(results)
        print("Saved regression baseline to evals/baseline.json")

    if args.compare_baseline:
        if not regression.has_baseline():
            print("No baseline found at evals/baseline.json. Run with --save-baseline first.")
        else:
            report = regression.run_and_compare(results)
            print("\nRegression comparison:")
            print(f"  Improved:  {report.improved}")
            print(f"  Regressed: {report.regressed}")
            print(f"  Unchanged: {len(report.unchanged)} queries")
            print(f"  New:       {report.new_queries}")
            print(f"  Removed:   {report.removed_queries}")
            print("  Summary deltas:")
            for metric, delta in sorted(report.summary.items()):
                print(f"    {metric}: {delta:+.3f}")

if __name__ == "__main__":
    main()
