"""Evaluation harness for the ALO RAG System.

Runs all test queries through the pipeline, computes per-query and
aggregate metrics, and returns structured results for downstream
analysis (failure analysis, regression comparison).

Requirements: 13.1, 14.1, 14.2, 14.3, 15.1, 15.2, 15.3
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from src.eval.metrics import GenerationMetrics, RetrievalMetrics
from src.models import EvalResult, TestQuery

if TYPE_CHECKING:
    from src.pipeline import Pipeline

logger = logging.getLogger(__name__)

# Default path to the test query suite
_DEFAULT_TEST_QUERIES_PATH = Path("evals/test_queries.json")


# ═══════════════════════════════════════════════════════════════════════════
# Aggregate metrics
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class AggregateMetrics:
    """Suite-level summary metrics across all evaluated queries."""

    mean_recall_at_5: float = 0.0
    mean_mrr: float = 0.0
    mean_context_precision: float = 0.0
    mean_faithfulness: float = 0.0
    mean_answer_relevance: float = 0.0
    hallucination_rate: float = 0.0
    mean_latency_ms: float = 0.0
    total_queries: int = 0
    queries_by_difficulty: dict[str, int] = field(default_factory=dict)
    queries_by_domain: dict[str, int] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# Test query loading
# ═══════════════════════════════════════════════════════════════════════════


def load_test_queries(path: Path | str = _DEFAULT_TEST_QUERIES_PATH) -> list[TestQuery]:
    """Load test queries from a JSON file.

    The JSON file is expected to have a top-level ``"queries"`` array
    where each element matches the :class:`TestQuery` schema.

    Parameters
    ----------
    path:
        Path to the test queries JSON file.

    Returns
    -------
    list[TestQuery]
        Parsed test queries ready for evaluation.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    json.JSONDecodeError
        If the file is not valid JSON.
    """
    path = Path(path)
    logger.info("Loading test queries from %s", path)

    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    raw_queries = data.get("queries", data if isinstance(data, list) else [])
    queries: list[TestQuery] = []

    for entry in raw_queries:
        queries.append(
            TestQuery(
                query_id=entry["query_id"],
                query=entry["query"],
                domain=entry["domain"],
                difficulty=entry["difficulty"],
                expected_answer=entry["expected_answer"],
                expected_chunk_ids=entry.get("expected_chunk_ids", []),
                customer_id=entry.get("customer_id"),
            )
        )

    logger.info("Loaded %d test queries", len(queries))
    return queries


# ═══════════════════════════════════════════════════════════════════════════
# Eval Harness
# ═══════════════════════════════════════════════════════════════════════════


class EvalHarness:
    """Runs the full evaluation suite and computes metrics.

    Parameters
    ----------
    pipeline:
        The RAG pipeline to evaluate.
    test_queries:
        List of test queries with ground-truth answers and expected
        chunk IDs.
    generation_metrics:
        Optional :class:`GenerationMetrics` instance.  If not provided,
        one is created from the pipeline's LLM client.
    """

    def __init__(
        self,
        pipeline: Pipeline,
        test_queries: list[TestQuery],
        generation_metrics: GenerationMetrics | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._test_queries = test_queries
        self._gen_metrics = generation_metrics or GenerationMetrics(
            pipeline._llm_client,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> list[EvalResult]:
        """Execute all test queries and compute per-query metrics.

        Each query is run through the pipeline.  Retrieval metrics are
        computed by comparing retrieved chunk IDs against the expected
        chunk IDs.  Generation metrics use LLM-as-judge evaluation.

        Returns
        -------
        list[EvalResult]
            One result per test query.
        """
        results: list[EvalResult] = []
        total = len(self._test_queries)

        logger.info("EvalHarness — starting evaluation of %d queries", total)

        for idx, tq in enumerate(self._test_queries, start=1):
            logger.info(
                "EvalHarness — [%d/%d] evaluating %s (%s, %s)",
                idx,
                total,
                tq.query_id,
                tq.domain,
                tq.difficulty,
            )

            try:
                result = self._evaluate_single(tq)
                results.append(result)
            except Exception:
                logger.exception(
                    "EvalHarness — failed to evaluate %s; recording zeros",
                    tq.query_id,
                )
                results.append(
                    EvalResult(
                        query_id=tq.query_id,
                        recall_at_5=0.0,
                        mrr=0.0,
                        context_precision=0.0,
                        faithfulness=0.0,
                        answer_relevance=0.0,
                        has_hallucination=True,
                        latency_ms=0.0,
                    )
                )

        logger.info("EvalHarness — evaluation complete: %d results", len(results))
        return results

    def compute_aggregate_metrics(
        self,
        results: list[EvalResult],
    ) -> AggregateMetrics:
        """Compute suite-level summary metrics from per-query results.

        Parameters
        ----------
        results:
            Per-query evaluation results (typically from :meth:`run`).

        Returns
        -------
        AggregateMetrics
            Aggregated metrics across the full suite.
        """
        if not results:
            return AggregateMetrics()

        n = len(results)

        # Count queries by difficulty and domain
        by_difficulty: dict[str, int] = {}
        by_domain: dict[str, int] = {}
        for tq in self._test_queries:
            by_difficulty[tq.difficulty] = by_difficulty.get(tq.difficulty, 0) + 1
            by_domain[tq.domain] = by_domain.get(tq.domain, 0) + 1

        return AggregateMetrics(
            mean_recall_at_5=sum(r.recall_at_5 for r in results) / n,
            mean_mrr=sum(r.mrr for r in results) / n,
            mean_context_precision=sum(r.context_precision for r in results) / n,
            mean_faithfulness=sum(r.faithfulness for r in results) / n,
            mean_answer_relevance=sum(r.answer_relevance for r in results) / n,
            hallucination_rate=GenerationMetrics.hallucination_rate(results),
            mean_latency_ms=sum(r.latency_ms for r in results) / n,
            total_queries=n,
            queries_by_difficulty=by_difficulty,
            queries_by_domain=by_domain,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evaluate_single(self, tq: TestQuery) -> EvalResult:
        """Run a single test query through the pipeline and score it."""
        # Run the pipeline
        t0 = time.perf_counter()
        pipeline_result = self._pipeline.run(
            query=tq.query,
            customer_id=tq.customer_id,
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0

        # Extract retrieved chunk IDs
        retrieved_ids = [rc.chunk.chunk_id for rc in pipeline_result.chunks]

        # ── Retrieval metrics ────────────────────────────────────────
        recall = RetrievalMetrics.recall_at_k(
            retrieved_ids, tq.expected_chunk_ids, k=5,
        )
        mrr = RetrievalMetrics.mrr(retrieved_ids, tq.expected_chunk_ids)
        precision = RetrievalMetrics.context_precision(
            retrieved_ids, tq.expected_chunk_ids,
        )

        # ── Generation metrics ───────────────────────────────────────
        context_texts = [rc.chunk.text for rc in pipeline_result.chunks]
        faithfulness = self._gen_metrics.faithfulness(
            answer=pipeline_result.answer,
            context=context_texts,
        )
        relevance = self._gen_metrics.answer_relevance(
            answer=pipeline_result.answer,
            query=tq.query,
        )

        # Threshold of 0.8 avoids flagging LLM-as-judge scoring noise as hallucination.
        # Scores between 0.8 and 1.0 reflect evaluator uncertainty, not actual
        # unsupported claims. Genuine hallucinations score below 0.8.
        has_hallucination = faithfulness < 0.8

        return EvalResult(
            query_id=tq.query_id,
            recall_at_5=recall,
            mrr=mrr,
            context_precision=precision,
            faithfulness=faithfulness,
            answer_relevance=relevance,
            has_hallucination=has_hallucination,
            latency_ms=latency_ms,
        )
