"""ALO RAG evaluation framework.

Provides metrics, an evaluation harness, failure analysis, and a
regression harness for measuring and tracking RAG system quality.
"""

# Lazy imports to avoid circular import warnings when running
# `python -m src.eval.harness` directly.


def __getattr__(name: str):
    if name in (
        "AggregateMetrics",
        "EvalHarness",
        "load_test_queries",
    ):
        from src.eval.harness import AggregateMetrics, EvalHarness, load_test_queries

        g = globals()
        g["AggregateMetrics"] = AggregateMetrics
        g["EvalHarness"] = EvalHarness
        g["load_test_queries"] = load_test_queries
        return g[name]

    if name in ("FailureAnalyzer", "FailureReport"):
        from src.eval.failure_analysis import FailureAnalyzer, FailureReport

        g = globals()
        g["FailureAnalyzer"] = FailureAnalyzer
        g["FailureReport"] = FailureReport
        return g[name]

    if name in ("GenerationMetrics", "RetrievalMetrics"):
        from src.eval.metrics import GenerationMetrics, RetrievalMetrics

        g = globals()
        g["GenerationMetrics"] = GenerationMetrics
        g["RetrievalMetrics"] = RetrievalMetrics
        return g[name]

    if name in ("RegressionHarness", "RegressionReport"):
        from src.eval.regression import RegressionHarness, RegressionReport

        g = globals()
        g["RegressionHarness"] = RegressionHarness
        g["RegressionReport"] = RegressionReport
        return g[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AggregateMetrics",
    "EvalHarness",
    "FailureAnalyzer",
    "FailureReport",
    "GenerationMetrics",
    "RetrievalMetrics",
    "RegressionHarness",
    "RegressionReport",
    "load_test_queries",
]
