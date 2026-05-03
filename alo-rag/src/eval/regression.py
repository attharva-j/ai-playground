"""Regression harness for the ALO RAG evaluation framework.

Compares current evaluation results against a stored baseline to detect
improvements and regressions across the test query suite.  Supports
saving new baselines after accepted runs.

Requirements: 16.2, 16.3
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.models import EvalResult

logger = logging.getLogger(__name__)

# Default baseline storage location
_DEFAULT_BASELINE_PATH = Path("evals/baseline.json")

# Threshold for classifying a metric change as improvement or regression.
# Changes within ±DELTA_THRESHOLD are considered "unchanged".
_DELTA_THRESHOLD = 0.05


@dataclass
class RegressionReport:
    """Comparison report between current results and a stored baseline."""

    improved: list[str] = field(default_factory=list)   # query_ids that improved
    regressed: list[str] = field(default_factory=list)  # query_ids that regressed
    unchanged: list[str] = field(default_factory=list)  # query_ids with no change
    new_queries: list[str] = field(default_factory=list)  # queries not in baseline
    removed_queries: list[str] = field(default_factory=list)  # baseline queries not in current
    summary: dict[str, float] = field(default_factory=dict)  # metric deltas


class RegressionHarness:
    """Compares current eval results against a stored baseline.

    Parameters
    ----------
    baseline_path:
        Path to the JSON file storing baseline results.
    delta_threshold:
        Minimum absolute change in combined score to classify a query
        as improved or regressed.  Defaults to 0.05.
    """

    def __init__(
        self,
        baseline_path: Path | str = _DEFAULT_BASELINE_PATH,
        delta_threshold: float = _DELTA_THRESHOLD,
    ) -> None:
        self._baseline_path = Path(baseline_path)
        self._delta_threshold = delta_threshold

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_and_compare(
        self,
        current_results: list[EvalResult],
    ) -> RegressionReport:
        """Compare *current_results* against the stored baseline.

        Parameters
        ----------
        current_results:
            Per-query evaluation results from the current run.

        Returns
        -------
        RegressionReport
            Classification of each query as improved, regressed, or
            unchanged, plus aggregate metric deltas.

        Raises
        ------
        FileNotFoundError
            If no baseline file exists at the configured path.
        """
        baseline = self._load_baseline()
        baseline_map = {r.query_id: r for r in baseline}
        current_map = {r.query_id: r for r in current_results}

        improved: list[str] = []
        regressed: list[str] = []
        unchanged: list[str] = []
        new_queries: list[str] = []
        removed_queries: list[str] = []

        # Classify each current query
        for qid, current in current_map.items():
            if qid not in baseline_map:
                new_queries.append(qid)
                continue

            base = baseline_map[qid]
            delta = self._combined_score(current) - self._combined_score(base)

            if delta > self._delta_threshold:
                improved.append(qid)
            elif delta < -self._delta_threshold:
                regressed.append(qid)
            else:
                unchanged.append(qid)

        # Identify removed queries (in baseline but not in current)
        for qid in baseline_map:
            if qid not in current_map:
                removed_queries.append(qid)

        # Compute aggregate metric deltas
        summary = self._compute_summary_deltas(baseline, current_results)

        report = RegressionReport(
            improved=improved,
            regressed=regressed,
            unchanged=unchanged,
            new_queries=new_queries,
            removed_queries=removed_queries,
            summary=summary,
        )

        logger.info(
            "RegressionHarness — improved=%d, regressed=%d, unchanged=%d, "
            "new=%d, removed=%d",
            len(improved),
            len(regressed),
            len(unchanged),
            len(new_queries),
            len(removed_queries),
        )

        return report

    def save_baseline(self, results: list[EvalResult]) -> None:
        """Persist evaluation results as the new baseline.

        Parameters
        ----------
        results:
            Per-query evaluation results to store.
        """
        self._baseline_path.parent.mkdir(parents=True, exist_ok=True)

        data = [
            {
                "query_id": r.query_id,
                "recall_at_5": r.recall_at_5,
                "mrr": r.mrr,
                "context_precision": r.context_precision,
                "faithfulness": r.faithfulness,
                "answer_relevance": r.answer_relevance,
                "has_hallucination": r.has_hallucination,
                "latency_ms": r.latency_ms,
            }
            for r in results
        ]

        with self._baseline_path.open("w", encoding="utf-8") as fh:
            json.dump(
                {"version": "1.0", "results": data},
                fh,
                indent=2,
            )

        logger.info(
            "RegressionHarness — saved baseline with %d results to %s",
            len(results),
            self._baseline_path,
        )

    def has_baseline(self) -> bool:
        """Return ``True`` if a baseline file exists."""
        return self._baseline_path.exists()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_baseline(self) -> list[EvalResult]:
        """Load baseline results from disk."""
        if not self._baseline_path.exists():
            raise FileNotFoundError(
                f"No baseline file found at {self._baseline_path}. "
                f"Run save_baseline() first to create one."
            )

        with self._baseline_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        raw_results = data.get("results", [])
        return [
            EvalResult(
                query_id=r["query_id"],
                recall_at_5=r["recall_at_5"],
                mrr=r["mrr"],
                context_precision=r["context_precision"],
                faithfulness=r["faithfulness"],
                answer_relevance=r["answer_relevance"],
                has_hallucination=r["has_hallucination"],
                latency_ms=r["latency_ms"],
            )
            for r in raw_results
        ]

    @staticmethod
    def _combined_score(result: EvalResult) -> float:
        """Average of the five core metrics (same formula as FailureAnalyzer)."""
        return (
            result.recall_at_5
            + result.mrr
            + result.context_precision
            + result.faithfulness
            + result.answer_relevance
        ) / 5.0

    @staticmethod
    def _compute_summary_deltas(
        baseline: list[EvalResult],
        current: list[EvalResult],
    ) -> dict[str, float]:
        """Compute mean metric deltas (current − baseline)."""
        metrics = [
            "recall_at_5",
            "mrr",
            "context_precision",
            "faithfulness",
            "answer_relevance",
            "latency_ms",
        ]

        def _mean(results: list[EvalResult], attr: str) -> float:
            if not results:
                return 0.0
            return sum(getattr(r, attr) for r in results) / len(results)

        return {
            f"delta_{m}": _mean(current, m) - _mean(baseline, m)
            for m in metrics
        }
