"""Unit tests for the query decomposer module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.models import IntentClassification, SubQuery
from src.query.decomposer import QueryDecomposer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_decomposer(classify_return: str | Exception = "") -> tuple[QueryDecomposer, MagicMock]:
    """Create a QueryDecomposer with a mocked LLMClient."""
    mock_llm = MagicMock()
    if isinstance(classify_return, Exception):
        mock_llm.classify.side_effect = classify_return
    else:
        mock_llm.classify.return_value = classify_return
    return QueryDecomposer(mock_llm), mock_llm


def _make_classification(
    domains: dict[str, float],
    primary_domain: str | None = None,
) -> IntentClassification:
    """Build an IntentClassification from domain scores."""
    max_score = max(domains.values()) if domains else 0.0
    if primary_domain is None:
        primary_domain = max(domains, key=domains.get) if domains else "product"  # type: ignore[arg-type]
    high_scoring = [d for d, s in domains.items() if s > 0.3]
    return IntentClassification(
        domains=domains,
        is_ambiguous=max_score < 0.3,
        is_multi_domain=len(high_scoring) >= 2,
        primary_domain=primary_domain,
    )


# ---------------------------------------------------------------------------
# decompose() — single-domain queries (no LLM call)
# ---------------------------------------------------------------------------


class TestDecomposeSingleDomain:
    """When only one domain scores above the threshold, return original query."""

    def test_single_domain_returns_one_sub_query(self) -> None:
        decomposer, mock_llm = _make_decomposer()
        classification = _make_classification(
            {"product": 0.9, "policy": 0.05, "customer": 0.05},
        )

        result = decomposer.decompose("What materials are the Airlift leggings?", classification)

        assert len(result) == 1
        assert result[0].text == "What materials are the Airlift leggings?"
        assert result[0].target_domain == "product"
        assert result[0].original_query == "What materials are the Airlift leggings?"
        mock_llm.classify.assert_not_called()

    def test_single_domain_no_llm_call(self) -> None:
        decomposer, mock_llm = _make_decomposer()
        classification = _make_classification(
            {"product": 0.1, "policy": 0.8, "customer": 0.1},
        )

        decomposer.decompose("What is the return policy?", classification)

        mock_llm.classify.assert_not_called()

    def test_zero_domains_above_threshold(self) -> None:
        """Ambiguous query — still returns single sub-query for primary domain."""
        decomposer, mock_llm = _make_decomposer()
        classification = _make_classification(
            {"product": 0.1, "policy": 0.1, "customer": 0.1},
        )

        result = decomposer.decompose("Hello there", classification)

        assert len(result) == 1
        assert result[0].target_domain == classification.primary_domain
        mock_llm.classify.assert_not_called()


# ---------------------------------------------------------------------------
# decompose() — multi-domain queries (LLM decomposition)
# ---------------------------------------------------------------------------


class TestDecomposeMultiDomain:
    """When 2+ domains score above threshold, use LLM to decompose."""

    def test_two_domain_decomposition(self) -> None:
        llm_response = json.dumps([
            {"text": "What is the return policy for sale items?", "domain": "policy"},
            {"text": "What leggings did I buy last month?", "domain": "customer"},
        ])
        decomposer, mock_llm = _make_decomposer(llm_response)
        classification = _make_classification(
            {"product": 0.1, "policy": 0.5, "customer": 0.4},
        )

        result = decomposer.decompose(
            "What's the return policy for the leggings I bought last month?",
            classification,
        )

        assert len(result) == 2
        assert result[0].target_domain == "policy"
        assert result[1].target_domain == "customer"
        assert all(
            sq.original_query == "What's the return policy for the leggings I bought last month?"
            for sq in result
        )
        mock_llm.classify.assert_called_once()

    def test_three_domain_decomposition(self) -> None:
        llm_response = json.dumps([
            {"text": "What are the Airlift leggings made of?", "domain": "product"},
            {"text": "What is the return policy?", "domain": "policy"},
            {"text": "What did I order last month?", "domain": "customer"},
        ])
        decomposer, _ = _make_decomposer(llm_response)
        classification = _make_classification(
            {"product": 0.4, "policy": 0.35, "customer": 0.35},
        )

        result = decomposer.decompose("complex query", classification)

        assert len(result) == 3
        domains = {sq.target_domain for sq in result}
        assert domains == {"product", "policy", "customer"}

    def test_filters_out_irrelevant_domains(self) -> None:
        """LLM returns a sub-query for a domain not in the relevant set — it's filtered."""
        llm_response = json.dumps([
            {"text": "What is the return policy?", "domain": "policy"},
            {"text": "What did I order?", "domain": "customer"},
            {"text": "What are the leggings?", "domain": "product"},
        ])
        decomposer, _ = _make_decomposer(llm_response)
        # Only policy and customer are above threshold
        classification = _make_classification(
            {"product": 0.1, "policy": 0.5, "customer": 0.4},
        )

        result = decomposer.decompose("test query", classification)

        assert len(result) == 2
        domains = {sq.target_domain for sq in result}
        assert "product" not in domains


# ---------------------------------------------------------------------------
# decompose() — error handling / graceful fallback
# ---------------------------------------------------------------------------


class TestDecomposeErrorHandling:
    """Tests for graceful error handling in decompose()."""

    def test_llm_exception_falls_back(self) -> None:
        decomposer, _ = _make_decomposer(RuntimeError("API timeout"))
        classification = _make_classification(
            {"product": 0.5, "policy": 0.4, "customer": 0.1},
        )

        result = decomposer.decompose("test query", classification)

        # Fallback: one sub-query per relevant domain with original text
        assert len(result) == 2
        assert all(sq.text == "test query" for sq in result)
        domains = {sq.target_domain for sq in result}
        assert domains == {"product", "policy"}

    def test_invalid_json_falls_back(self) -> None:
        decomposer, _ = _make_decomposer("This is not JSON")
        classification = _make_classification(
            {"product": 0.5, "policy": 0.4, "customer": 0.1},
        )

        result = decomposer.decompose("test query", classification)

        assert len(result) == 2
        assert all(sq.text == "test query" for sq in result)

    def test_json_not_a_list_falls_back(self) -> None:
        decomposer, _ = _make_decomposer('{"text": "hello", "domain": "product"}')
        classification = _make_classification(
            {"product": 0.5, "policy": 0.4, "customer": 0.1},
        )

        result = decomposer.decompose("test query", classification)

        assert len(result) == 2
        assert all(sq.text == "test query" for sq in result)

    def test_empty_list_falls_back(self) -> None:
        decomposer, _ = _make_decomposer("[]")
        classification = _make_classification(
            {"product": 0.5, "policy": 0.4, "customer": 0.1},
        )

        result = decomposer.decompose("test query", classification)

        assert len(result) == 2

    def test_json_with_markdown_fences(self) -> None:
        inner = json.dumps([
            {"text": "What is the return policy?", "domain": "policy"},
            {"text": "What did I order?", "domain": "customer"},
        ])
        response = f"```json\n{inner}\n```"
        decomposer, _ = _make_decomposer(response)
        classification = _make_classification(
            {"product": 0.1, "policy": 0.5, "customer": 0.4},
        )

        result = decomposer.decompose("test query", classification)

        assert len(result) == 2

    def test_sub_query_with_empty_text_is_skipped(self) -> None:
        llm_response = json.dumps([
            {"text": "", "domain": "policy"},
            {"text": "What did I order?", "domain": "customer"},
        ])
        decomposer, _ = _make_decomposer(llm_response)
        classification = _make_classification(
            {"product": 0.1, "policy": 0.5, "customer": 0.4},
        )

        result = decomposer.decompose("test query", classification)

        assert len(result) == 1
        assert result[0].target_domain == "customer"

    def test_sub_query_with_missing_domain_is_skipped(self) -> None:
        llm_response = json.dumps([
            {"text": "What is the return policy?"},
            {"text": "What did I order?", "domain": "customer"},
        ])
        decomposer, _ = _make_decomposer(llm_response)
        classification = _make_classification(
            {"product": 0.1, "policy": 0.5, "customer": 0.4},
        )

        result = decomposer.decompose("test query", classification)

        assert len(result) == 1
        assert result[0].target_domain == "customer"

    def test_all_sub_queries_invalid_falls_back(self) -> None:
        """If every parsed sub-query is invalid, fall back to original query."""
        llm_response = json.dumps([
            {"text": "", "domain": "policy"},
            {"domain": "customer"},
        ])
        decomposer, _ = _make_decomposer(llm_response)
        classification = _make_classification(
            {"product": 0.1, "policy": 0.5, "customer": 0.4},
        )

        result = decomposer.decompose("test query", classification)

        # Fallback: one per relevant domain
        assert len(result) == 2
        assert all(sq.text == "test query" for sq in result)


# ---------------------------------------------------------------------------
# decompose() — SubQuery structure
# ---------------------------------------------------------------------------


class TestSubQueryStructure:
    """Verify SubQuery fields are populated correctly."""

    def test_original_query_preserved(self) -> None:
        llm_response = json.dumps([
            {"text": "Sub-query 1", "domain": "policy"},
            {"text": "Sub-query 2", "domain": "customer"},
        ])
        decomposer, _ = _make_decomposer(llm_response)
        classification = _make_classification(
            {"product": 0.1, "policy": 0.5, "customer": 0.4},
        )

        original = "What's the return policy for my order?"
        result = decomposer.decompose(original, classification)

        for sq in result:
            assert sq.original_query == original

    def test_sub_query_is_dataclass_instance(self) -> None:
        decomposer, _ = _make_decomposer()
        classification = _make_classification(
            {"product": 0.9, "policy": 0.05, "customer": 0.05},
        )

        result = decomposer.decompose("test", classification)

        assert isinstance(result[0], SubQuery)
