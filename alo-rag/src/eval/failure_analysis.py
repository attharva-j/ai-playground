"""Failure analysis for the ALO RAG evaluation framework.

Identifies the worst-performing queries from an evaluation run and
produces detailed failure reports with retrieval issues, generation
issues, and actionable recommendations.

Requirements: 16.1
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.models import EvalResult

logger = logging.getLogger(__name__)

# Thresholds for diagnosing issues
_LOW_RECALL_THRESHOLD = 0.5
_LOW_PRECISION_THRESHOLD = 0.3
_LOW_MRR_THRESHOLD = 0.5
_LOW_FAITHFULNESS_THRESHOLD = 0.7
_LOW_RELEVANCE_THRESHOLD = 0.6


@dataclass
class FailureReport:
    """Detailed failure analysis for a single underperforming query."""

    query_id: str
    query: str
    combined_score: float
    retrieval_issues: list[str] = field(default_factory=list)
    generation_issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


class FailureAnalyzer:
    """Identifies worst-performing queries and produces failure reports.

    Parameters
    ----------
    query_lookup:
        Mapping from ``query_id`` to the original query text.  Used to
        populate the ``query`` field in :class:`FailureReport`.  If not
        provided, the query text defaults to ``"<unknown>"``.
    """

    def __init__(
        self,
        query_lookup: dict[str, str] | None = None,
    ) -> None:
        self._query_lookup = query_lookup or {}

    def analyze(
        self,
        results: list[EvalResult],
        top_n: int = 3,
    ) -> list[FailureReport]:
        """Identify the *top_n* worst-performing queries and diagnose them.

        The combined score for ranking is the average of all per-query
        metrics (recall@5, MRR, context precision, faithfulness, answer
        relevance).  Lower combined scores indicate worse performance.

        Parameters
        ----------
        results:
            Per-query evaluation results from :class:`EvalHarness`.
        top_n:
            Number of worst-performing queries to analyse.

        Returns
        -------
        list[FailureReport]
            Failure reports ordered from worst to best (ascending
            combined score).
        """
        if not results:
            return []

        # Compute combined score and sort ascending (worst first)
        scored = [
            (r, self._combined_score(r))
            for r in results
        ]
        scored.sort(key=lambda pair: pair[1])

        reports: list[FailureReport] = []
        for result, score in scored[:top_n]:
            report = self._build_report(result, score)
            reports.append(report)
            logger.info(
                "FailureAnalyzer — %s: combined=%.3f, retrieval_issues=%d, "
                "generation_issues=%d",
                report.query_id,
                report.combined_score,
                len(report.retrieval_issues),
                len(report.generation_issues),
            )

        return reports

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _combined_score(result: EvalResult) -> float:
        """Average of all per-query metrics (lower = worse)."""
        return (
            result.recall_at_5
            + result.mrr
            + result.context_precision
            + result.faithfulness
            + result.answer_relevance
        ) / 5.0

    def _build_report(
        self,
        result: EvalResult,
        combined_score: float,
    ) -> FailureReport:
        """Diagnose a single underperforming query."""
        retrieval_issues: list[str] = []
        generation_issues: list[str] = []
        recommendations: list[str] = []

        query_text = self._query_lookup.get(result.query_id, "<unknown>")

        # ── Retrieval diagnosis ──────────────────────────────────────
        if result.recall_at_5 < _LOW_RECALL_THRESHOLD:
            retrieval_issues.append(
                f"Low Recall@5 ({result.recall_at_5:.2f}): relevant chunks "
                f"are not appearing in the top-5 results."
            )
            recommendations.append(
                "Review chunking strategy for this query's domain. "
                "Consider adjusting chunk boundaries or adding metadata "
                "to improve retrieval coverage."
            )

        if result.context_precision < _LOW_PRECISION_THRESHOLD:
            retrieval_issues.append(
                f"Low Context Precision ({result.context_precision:.2f}): "
                f"many retrieved chunks are irrelevant."
            )
            recommendations.append(
                "Tighten metadata filters or adjust RRF fusion weights "
                "to reduce noise in retrieval results."
            )

        if result.mrr < _LOW_MRR_THRESHOLD:
            retrieval_issues.append(
                f"Low MRR ({result.mrr:.2f}): the first relevant chunk "
                f"appears too late in the ranked list."
            )
            recommendations.append(
                "Investigate cross-encoder reranking effectiveness for "
                "this query type. The reranker may not be surfacing the "
                "most relevant chunk to the top position."
            )

        # ── Generation diagnosis ─────────────────────────────────────
        if result.faithfulness < _LOW_FAITHFULNESS_THRESHOLD:
            generation_issues.append(
                f"Low Faithfulness ({result.faithfulness:.2f}): the answer "
                f"contains claims not supported by the retrieved context."
            )
            recommendations.append(
                "Review the faithfulness guardrail prompt. Consider "
                "strengthening the system instruction to constrain the "
                "LLM to only use provided context."
            )

        if result.answer_relevance < _LOW_RELEVANCE_THRESHOLD:
            generation_issues.append(
                f"Low Answer Relevance ({result.answer_relevance:.2f}): "
                f"the answer does not adequately address the query."
            )
            recommendations.append(
                "Check whether the retrieved context contains the "
                "information needed to answer this query. If retrieval "
                "is adequate, adjust the generation prompt to better "
                "focus on the user's question."
            )

        if result.has_hallucination:
            generation_issues.append(
                "Hallucination detected: at least one unsupported claim "
                "was present in the generated answer."
            )

        # If no specific issues were found, note the general low score
        if not retrieval_issues and not generation_issues:
            generation_issues.append(
                f"Combined score is low ({combined_score:.2f}) but no "
                f"single metric is critically below threshold. This may "
                f"indicate marginal performance across multiple dimensions."
            )
            recommendations.append(
                "Consider this query as a candidate for targeted "
                "improvement across both retrieval and generation."
            )

        return FailureReport(
            query_id=result.query_id,
            query=query_text,
            combined_score=combined_score,
            retrieval_issues=retrieval_issues,
            generation_issues=generation_issues,
            recommendations=recommendations,
        )
