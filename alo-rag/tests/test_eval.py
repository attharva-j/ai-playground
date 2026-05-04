"""Unit tests for the evaluation framework.

Covers:
- RetrievalMetrics computations with known inputs and expected outputs
- GenerationMetrics.hallucination_rate() calculation
- FailureAnalyzer selects correct worst-performing queries
- RegressionHarness detects improvements and regressions

Requirements: 14.1, 14.2, 14.3, 15.3, 16.1, 16.2
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.eval.failure_analysis import FailureAnalyzer, FailureReport
from src.eval.metrics import GenerationMetrics, RetrievalMetrics
from src.eval.regression import RegressionHarness, RegressionReport
from src.models import EvalResult
from src.eval.harness import load_test_queries


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_eval_result(
    query_id: str = "TQ-001",
    recall_at_5: float = 0.8,
    mrr: float = 1.0,
    context_precision: float = 0.6,
    faithfulness: float = 0.9,
    answer_relevance: float = 0.85,
    has_hallucination: bool = False,
    latency_ms: float = 500.0,
) -> EvalResult:
    """Create an EvalResult with sensible defaults."""
    return EvalResult(
        query_id=query_id,
        recall_at_5=recall_at_5,
        mrr=mrr,
        context_precision=context_precision,
        faithfulness=faithfulness,
        answer_relevance=answer_relevance,
        has_hallucination=has_hallucination,
        latency_ms=latency_ms,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. RetrievalMetrics — Recall@k (R14.1)
# ═══════════════════════════════════════════════════════════════════════════


class TestRecallAtK:
    """Verify Recall@k computation (R14.1)."""

    def test_perfect_recall(self) -> None:
        retrieved = ["A", "B", "C", "D", "E"]
        relevant = ["A", "B", "C"]
        assert RetrievalMetrics.recall_at_k(retrieved, relevant, k=5) == 1.0

    def test_partial_recall(self) -> None:
        retrieved = ["A", "B", "X", "Y", "Z"]
        relevant = ["A", "B", "C", "D"]
        # 2 out of 4 relevant found in top-5
        assert RetrievalMetrics.recall_at_k(retrieved, relevant, k=5) == 0.5

    def test_zero_recall(self) -> None:
        retrieved = ["X", "Y", "Z"]
        relevant = ["A", "B"]
        assert RetrievalMetrics.recall_at_k(retrieved, relevant, k=5) == 0.0

    def test_k_limits_retrieved(self) -> None:
        # Relevant chunk at position 4 (index 3) — within k=3 it's missed
        retrieved = ["X", "Y", "Z", "A", "B"]
        relevant = ["A"]
        assert RetrievalMetrics.recall_at_k(retrieved, relevant, k=3) == 0.0
        # With k=5 it's found
        assert RetrievalMetrics.recall_at_k(retrieved, relevant, k=5) == 1.0

    def test_empty_relevant_returns_zero(self) -> None:
        assert RetrievalMetrics.recall_at_k(["A", "B"], [], k=5) == 0.0

    def test_empty_retrieved_returns_zero(self) -> None:
        assert RetrievalMetrics.recall_at_k([], ["A"], k=5) == 0.0

    def test_duplicate_retrieved_ids(self) -> None:
        # Duplicates in retrieved shouldn't inflate recall
        retrieved = ["A", "A", "A", "A", "A"]
        relevant = ["A", "B"]
        assert RetrievalMetrics.recall_at_k(retrieved, relevant, k=5) == 0.5


# ═══════════════════════════════════════════════════════════════════════════
# 2. RetrievalMetrics — MRR (R14.2)
# ═══════════════════════════════════════════════════════════════════════════


class TestMRR:
    """Verify Mean Reciprocal Rank computation (R14.2)."""

    def test_relevant_at_rank_1(self) -> None:
        retrieved = ["A", "B", "C"]
        relevant = ["A"]
        assert RetrievalMetrics.mrr(retrieved, relevant) == 1.0

    def test_relevant_at_rank_2(self) -> None:
        retrieved = ["X", "A", "B"]
        relevant = ["A"]
        assert RetrievalMetrics.mrr(retrieved, relevant) == 0.5

    def test_relevant_at_rank_3(self) -> None:
        retrieved = ["X", "Y", "A"]
        relevant = ["A"]
        assert RetrievalMetrics.mrr(retrieved, relevant) == pytest.approx(1.0 / 3.0)

    def test_no_relevant_returns_zero(self) -> None:
        retrieved = ["X", "Y", "Z"]
        relevant = ["A"]
        assert RetrievalMetrics.mrr(retrieved, relevant) == 0.0

    def test_first_relevant_used_when_multiple(self) -> None:
        # MRR uses the rank of the *first* relevant chunk
        retrieved = ["X", "A", "B"]
        relevant = ["A", "B"]
        assert RetrievalMetrics.mrr(retrieved, relevant) == 0.5

    def test_empty_retrieved(self) -> None:
        assert RetrievalMetrics.mrr([], ["A"]) == 0.0

    def test_empty_relevant(self) -> None:
        assert RetrievalMetrics.mrr(["A", "B"], []) == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# 3. RetrievalMetrics — Context Precision (R14.3)
# ═══════════════════════════════════════════════════════════════════════════


class TestContextPrecision:
    """Verify Context Precision computation (R14.3)."""

    def test_all_relevant(self) -> None:
        retrieved = ["A", "B", "C"]
        relevant = ["A", "B", "C"]
        assert RetrievalMetrics.context_precision(retrieved, relevant) == 1.0

    def test_none_relevant(self) -> None:
        retrieved = ["X", "Y", "Z"]
        relevant = ["A", "B"]
        assert RetrievalMetrics.context_precision(retrieved, relevant) == 0.0

    def test_partial_precision(self) -> None:
        retrieved = ["A", "X", "B", "Y"]
        relevant = ["A", "B"]
        # 2 out of 4 retrieved are relevant
        assert RetrievalMetrics.context_precision(retrieved, relevant) == 0.5

    def test_empty_retrieved_returns_zero(self) -> None:
        assert RetrievalMetrics.context_precision([], ["A"]) == 0.0

    def test_single_relevant_in_many(self) -> None:
        retrieved = ["X", "Y", "Z", "W", "A"]
        relevant = ["A"]
        assert RetrievalMetrics.context_precision(retrieved, relevant) == 0.2


# ═══════════════════════════════════════════════════════════════════════════
# 4. GenerationMetrics — Hallucination Rate (R15.3)
# ═══════════════════════════════════════════════════════════════════════════


class TestHallucinationRate:
    """Verify hallucination_rate() static method (R15.3)."""

    def test_no_hallucinations(self) -> None:
        results = [
            _make_eval_result("TQ-001", has_hallucination=False),
            _make_eval_result("TQ-002", has_hallucination=False),
            _make_eval_result("TQ-003", has_hallucination=False),
        ]
        assert GenerationMetrics.hallucination_rate(results) == 0.0

    def test_all_hallucinations(self) -> None:
        results = [
            _make_eval_result("TQ-001", has_hallucination=True),
            _make_eval_result("TQ-002", has_hallucination=True),
        ]
        assert GenerationMetrics.hallucination_rate(results) == 1.0

    def test_partial_hallucinations(self) -> None:
        results = [
            _make_eval_result("TQ-001", has_hallucination=True),
            _make_eval_result("TQ-002", has_hallucination=False),
            _make_eval_result("TQ-003", has_hallucination=True),
            _make_eval_result("TQ-004", has_hallucination=False),
        ]
        assert GenerationMetrics.hallucination_rate(results) == 0.5

    def test_single_result_with_hallucination(self) -> None:
        results = [_make_eval_result("TQ-001", has_hallucination=True)]
        assert GenerationMetrics.hallucination_rate(results) == 1.0

    def test_single_result_without_hallucination(self) -> None:
        results = [_make_eval_result("TQ-001", has_hallucination=False)]
        assert GenerationMetrics.hallucination_rate(results) == 0.0

    def test_empty_results_returns_zero(self) -> None:
        assert GenerationMetrics.hallucination_rate([]) == 0.0

    def test_one_of_three_hallucinated(self) -> None:
        results = [
            _make_eval_result("TQ-001", has_hallucination=False),
            _make_eval_result("TQ-002", has_hallucination=True),
            _make_eval_result("TQ-003", has_hallucination=False),
        ]
        assert GenerationMetrics.hallucination_rate(results) == pytest.approx(1.0 / 3.0)


# ═══════════════════════════════════════════════════════════════════════════
# 5. FailureAnalyzer (R16.1)
# ═══════════════════════════════════════════════════════════════════════════


class TestFailureAnalyzerSelection:
    """Verify FailureAnalyzer selects the correct worst-performing queries."""

    def test_selects_three_worst(self) -> None:
        """The 3 queries with the lowest combined score should be selected."""
        results = [
            # combined = (0.8+1.0+0.6+0.9+0.85)/5 = 0.83
            _make_eval_result("TQ-001", recall_at_5=0.8, mrr=1.0, context_precision=0.6,
                              faithfulness=0.9, answer_relevance=0.85),
            # combined = (0.2+0.25+0.1+0.3+0.15)/5 = 0.20
            _make_eval_result("TQ-002", recall_at_5=0.2, mrr=0.25, context_precision=0.1,
                              faithfulness=0.3, answer_relevance=0.15),
            # combined = (0.0+0.0+0.0+0.5+0.5)/5 = 0.20
            _make_eval_result("TQ-003", recall_at_5=0.0, mrr=0.0, context_precision=0.0,
                              faithfulness=0.5, answer_relevance=0.5),
            # combined = (1.0+1.0+1.0+1.0+1.0)/5 = 1.0
            _make_eval_result("TQ-004", recall_at_5=1.0, mrr=1.0, context_precision=1.0,
                              faithfulness=1.0, answer_relevance=1.0),
            # combined = (0.4+0.33+0.2+0.6+0.5)/5 = 0.406
            _make_eval_result("TQ-005", recall_at_5=0.4, mrr=0.33, context_precision=0.2,
                              faithfulness=0.6, answer_relevance=0.5),
        ]

        analyzer = FailureAnalyzer()
        reports = analyzer.analyze(results, top_n=3)

        assert len(reports) == 3
        report_ids = [r.query_id for r in reports]
        # TQ-002 (0.20), TQ-003 (0.20), TQ-005 (0.406) are the 3 worst
        assert "TQ-002" in report_ids
        assert "TQ-003" in report_ids
        assert "TQ-005" in report_ids
        # TQ-001 and TQ-004 should NOT be in the worst 3
        assert "TQ-004" not in report_ids
        assert "TQ-001" not in report_ids

    def test_sorted_ascending_by_combined_score(self) -> None:
        """Reports should be ordered worst-first (ascending combined score)."""
        results = [
            # combined = 0.83
            _make_eval_result("TQ-HIGH", recall_at_5=0.8, mrr=1.0, context_precision=0.6,
                              faithfulness=0.9, answer_relevance=0.85),
            # combined = 0.20
            _make_eval_result("TQ-LOW", recall_at_5=0.2, mrr=0.25, context_precision=0.1,
                              faithfulness=0.3, answer_relevance=0.15),
            # combined = 0.50
            _make_eval_result("TQ-MID", recall_at_5=0.5, mrr=0.5, context_precision=0.5,
                              faithfulness=0.5, answer_relevance=0.5),
        ]

        analyzer = FailureAnalyzer()
        reports = analyzer.analyze(results, top_n=3)

        assert reports[0].query_id == "TQ-LOW"
        assert reports[1].query_id == "TQ-MID"
        assert reports[2].query_id == "TQ-HIGH"

    def test_top_n_larger_than_results(self) -> None:
        """When top_n exceeds result count, return all results."""
        results = [
            _make_eval_result("TQ-001"),
            _make_eval_result("TQ-002"),
        ]

        analyzer = FailureAnalyzer()
        reports = analyzer.analyze(results, top_n=5)

        assert len(reports) == 2

    def test_empty_results(self) -> None:
        analyzer = FailureAnalyzer()
        reports = analyzer.analyze([], top_n=3)
        assert reports == []

    def test_query_lookup_populates_query_text(self) -> None:
        results = [_make_eval_result("TQ-001")]
        lookup = {"TQ-001": "What fabric is the Airlift legging?"}

        analyzer = FailureAnalyzer(query_lookup=lookup)
        reports = analyzer.analyze(results, top_n=1)

        assert reports[0].query == "What fabric is the Airlift legging?"

    def test_missing_query_lookup_defaults_to_unknown(self) -> None:
        results = [_make_eval_result("TQ-001")]

        analyzer = FailureAnalyzer()
        reports = analyzer.analyze(results, top_n=1)

        assert reports[0].query == "<unknown>"


class TestFailureAnalyzerDiagnosis:
    """Verify FailureAnalyzer produces correct diagnoses."""

    def test_low_recall_flagged(self) -> None:
        results = [
            _make_eval_result("TQ-001", recall_at_5=0.2, mrr=1.0,
                              context_precision=0.8, faithfulness=1.0,
                              answer_relevance=1.0),
        ]
        analyzer = FailureAnalyzer()
        reports = analyzer.analyze(results, top_n=1)

        assert len(reports[0].retrieval_issues) >= 1
        assert any("Recall@5" in issue for issue in reports[0].retrieval_issues)

    def test_low_precision_flagged(self) -> None:
        results = [
            _make_eval_result("TQ-001", recall_at_5=1.0, mrr=1.0,
                              context_precision=0.1, faithfulness=1.0,
                              answer_relevance=1.0),
        ]
        analyzer = FailureAnalyzer()
        reports = analyzer.analyze(results, top_n=1)

        assert any("Precision" in issue for issue in reports[0].retrieval_issues)

    def test_low_faithfulness_flagged(self) -> None:
        results = [
            _make_eval_result("TQ-001", recall_at_5=1.0, mrr=1.0,
                              context_precision=1.0, faithfulness=0.3,
                              answer_relevance=1.0),
        ]
        analyzer = FailureAnalyzer()
        reports = analyzer.analyze(results, top_n=1)

        assert any("Faithfulness" in issue for issue in reports[0].generation_issues)

    def test_hallucination_flagged(self) -> None:
        results = [
            _make_eval_result("TQ-001", has_hallucination=True),
        ]
        analyzer = FailureAnalyzer()
        reports = analyzer.analyze(results, top_n=1)

        assert any("Hallucination" in issue for issue in reports[0].generation_issues)

    def test_recommendations_provided(self) -> None:
        """Every report should have at least one recommendation."""
        results = [
            _make_eval_result("TQ-001", recall_at_5=0.1, faithfulness=0.2),
        ]
        analyzer = FailureAnalyzer()
        reports = analyzer.analyze(results, top_n=1)

        assert len(reports[0].recommendations) >= 1


# ═══════════════════════════════════════════════════════════════════════════
# 6. RegressionHarness (R16.2)
# ═══════════════════════════════════════════════════════════════════════════


class TestRegressionHarness:
    """Verify RegressionHarness detects improvements and regressions."""

    def test_detects_improvement(self, tmp_path: Path) -> None:
        """A query whose combined score increased beyond the threshold."""
        baseline = [
            _make_eval_result("TQ-001", recall_at_5=0.4, mrr=0.5,
                              context_precision=0.3, faithfulness=0.5,
                              answer_relevance=0.4),
        ]
        current = [
            _make_eval_result("TQ-001", recall_at_5=0.9, mrr=1.0,
                              context_precision=0.8, faithfulness=0.95,
                              answer_relevance=0.9),
        ]

        baseline_path = tmp_path / "baseline.json"
        harness = RegressionHarness(baseline_path=baseline_path)
        harness.save_baseline(baseline)

        report = harness.run_and_compare(current)

        assert "TQ-001" in report.improved
        assert "TQ-001" not in report.regressed
        assert "TQ-001" not in report.unchanged

    def test_detects_regression(self, tmp_path: Path) -> None:
        """A query whose combined score decreased beyond the threshold."""
        baseline = [
            _make_eval_result("TQ-001", recall_at_5=0.9, mrr=1.0,
                              context_precision=0.8, faithfulness=0.95,
                              answer_relevance=0.9),
        ]
        current = [
            _make_eval_result("TQ-001", recall_at_5=0.2, mrr=0.25,
                              context_precision=0.1, faithfulness=0.3,
                              answer_relevance=0.2),
        ]

        baseline_path = tmp_path / "baseline.json"
        harness = RegressionHarness(baseline_path=baseline_path)
        harness.save_baseline(baseline)

        report = harness.run_and_compare(current)

        assert "TQ-001" in report.regressed
        assert "TQ-001" not in report.improved

    def test_detects_unchanged(self, tmp_path: Path) -> None:
        """A query whose combined score changed less than the threshold."""
        result = _make_eval_result("TQ-001", recall_at_5=0.8, mrr=1.0,
                                   context_precision=0.6, faithfulness=0.9,
                                   answer_relevance=0.85)

        baseline_path = tmp_path / "baseline.json"
        harness = RegressionHarness(baseline_path=baseline_path)
        harness.save_baseline([result])

        # Same result — delta is 0
        report = harness.run_and_compare([result])

        assert "TQ-001" in report.unchanged
        assert "TQ-001" not in report.improved
        assert "TQ-001" not in report.regressed

    def test_new_queries_detected(self, tmp_path: Path) -> None:
        """Queries in current but not in baseline are flagged as new."""
        baseline = [_make_eval_result("TQ-001")]
        current = [_make_eval_result("TQ-001"), _make_eval_result("TQ-002")]

        baseline_path = tmp_path / "baseline.json"
        harness = RegressionHarness(baseline_path=baseline_path)
        harness.save_baseline(baseline)

        report = harness.run_and_compare(current)

        assert "TQ-002" in report.new_queries

    def test_removed_queries_detected(self, tmp_path: Path) -> None:
        """Queries in baseline but not in current are flagged as removed."""
        baseline = [_make_eval_result("TQ-001"), _make_eval_result("TQ-002")]
        current = [_make_eval_result("TQ-001")]

        baseline_path = tmp_path / "baseline.json"
        harness = RegressionHarness(baseline_path=baseline_path)
        harness.save_baseline(baseline)

        report = harness.run_and_compare(current)

        assert "TQ-002" in report.removed_queries

    def test_summary_deltas_computed(self, tmp_path: Path) -> None:
        """Summary should contain metric deltas (current - baseline)."""
        baseline = [
            _make_eval_result("TQ-001", recall_at_5=0.5, mrr=0.5,
                              context_precision=0.5, faithfulness=0.5,
                              answer_relevance=0.5, latency_ms=1000.0),
        ]
        current = [
            _make_eval_result("TQ-001", recall_at_5=0.8, mrr=0.8,
                              context_precision=0.8, faithfulness=0.8,
                              answer_relevance=0.8, latency_ms=800.0),
        ]

        baseline_path = tmp_path / "baseline.json"
        harness = RegressionHarness(baseline_path=baseline_path)
        harness.save_baseline(baseline)

        report = harness.run_and_compare(current)

        assert report.summary["delta_recall_at_5"] == pytest.approx(0.3)
        assert report.summary["delta_mrr"] == pytest.approx(0.3)
        assert report.summary["delta_faithfulness"] == pytest.approx(0.3)
        assert report.summary["delta_latency_ms"] == pytest.approx(-200.0)

    def test_missing_baseline_raises(self, tmp_path: Path) -> None:
        """run_and_compare should raise FileNotFoundError with no baseline."""
        baseline_path = tmp_path / "nonexistent.json"
        harness = RegressionHarness(baseline_path=baseline_path)

        with pytest.raises(FileNotFoundError):
            harness.run_and_compare([_make_eval_result("TQ-001")])

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Saved baseline should be loadable and produce correct comparisons."""
        original = [
            _make_eval_result("TQ-001", recall_at_5=0.7, mrr=0.8,
                              context_precision=0.6, faithfulness=0.9,
                              answer_relevance=0.85, has_hallucination=False,
                              latency_ms=450.0),
        ]

        baseline_path = tmp_path / "baseline.json"
        harness = RegressionHarness(baseline_path=baseline_path)
        harness.save_baseline(original)

        # Verify the file was written
        assert baseline_path.exists()

        # Load and compare with identical data — should be unchanged
        report = harness.run_and_compare(original)
        assert "TQ-001" in report.unchanged

    def test_has_baseline(self, tmp_path: Path) -> None:
        baseline_path = tmp_path / "baseline.json"
        harness = RegressionHarness(baseline_path=baseline_path)

        assert harness.has_baseline() is False

        harness.save_baseline([_make_eval_result("TQ-001")])
        assert harness.has_baseline() is True

    def test_mixed_improvements_and_regressions(self, tmp_path: Path) -> None:
        """Multiple queries with different trajectories."""
        baseline = [
            # Will improve
            _make_eval_result("TQ-001", recall_at_5=0.3, mrr=0.3,
                              context_precision=0.3, faithfulness=0.3,
                              answer_relevance=0.3),
            # Will regress
            _make_eval_result("TQ-002", recall_at_5=0.9, mrr=0.9,
                              context_precision=0.9, faithfulness=0.9,
                              answer_relevance=0.9),
            # Will stay the same
            _make_eval_result("TQ-003", recall_at_5=0.5, mrr=0.5,
                              context_precision=0.5, faithfulness=0.5,
                              answer_relevance=0.5),
        ]
        current = [
            _make_eval_result("TQ-001", recall_at_5=0.9, mrr=0.9,
                              context_precision=0.9, faithfulness=0.9,
                              answer_relevance=0.9),
            _make_eval_result("TQ-002", recall_at_5=0.2, mrr=0.2,
                              context_precision=0.2, faithfulness=0.2,
                              answer_relevance=0.2),
            _make_eval_result("TQ-003", recall_at_5=0.5, mrr=0.5,
                              context_precision=0.5, faithfulness=0.5,
                              answer_relevance=0.5),
        ]

        baseline_path = tmp_path / "baseline.json"
        harness = RegressionHarness(baseline_path=baseline_path)
        harness.save_baseline(baseline)

        report = harness.run_and_compare(current)

        assert "TQ-001" in report.improved
        assert "TQ-002" in report.regressed
        assert "TQ-003" in report.unchanged

    def test_custom_delta_threshold(self, tmp_path: Path) -> None:
        """A tighter threshold should classify small changes as regressions."""
        baseline = [
            _make_eval_result("TQ-001", recall_at_5=0.5, mrr=0.5,
                              context_precision=0.5, faithfulness=0.5,
                              answer_relevance=0.5),
        ]
        # Small decrease: combined goes from 0.5 to 0.48
        current = [
            _make_eval_result("TQ-001", recall_at_5=0.48, mrr=0.48,
                              context_precision=0.48, faithfulness=0.48,
                              answer_relevance=0.48),
        ]

        baseline_path = tmp_path / "baseline.json"

        # Default threshold (0.05) — should be unchanged
        harness_default = RegressionHarness(baseline_path=baseline_path)
        harness_default.save_baseline(baseline)
        report_default = harness_default.run_and_compare(current)
        assert "TQ-001" in report_default.unchanged

        # Tight threshold (0.01) — should detect regression
        harness_tight = RegressionHarness(baseline_path=baseline_path,
                                          delta_threshold=0.01)
        report_tight = harness_tight.run_and_compare(current)
        assert "TQ-001" in report_tight.regressed
    
    def test_load_test_queries_parses_expected_behavior(tmp_path: Path) -> None:
        path = tmp_path / "queries.json"
        path.write_text(
            json.dumps(
                {
                    "queries": [
                        {
                            "query_id": "TQ-X",
                            "query": "What is my order status?",
                            "domain": "customer",
                            "difficulty": "easy",
                            "expected_answer": "Need customer context.",
                            "expected_chunk_ids": [],
                            "customer_id": None,
                            "expected_behavior": "clarify",
                            "requires_customer_context": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        queries = load_test_queries(path)

        assert queries[0].expected_behavior == "clarify"
        assert queries[0].requires_customer_context is True
