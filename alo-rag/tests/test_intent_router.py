"""Unit tests for the intent router module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.models import IntentClassification
from src.query.intent_router import (
    AMBIGUITY_THRESHOLD,
    HYDE_THRESHOLD,
    MULTI_DOMAIN_THRESHOLD,
    IntentRouter,
    _CLASSIFICATION_SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_router(classify_return: str) -> tuple[IntentRouter, MagicMock]:
    """Create an IntentRouter with a mocked LLMClient returning *classify_return*."""
    mock_llm = MagicMock()
    mock_llm.classify.return_value = classify_return
    return IntentRouter(mock_llm), mock_llm


# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------


class TestThresholdConstants:
    """Verify threshold constants match the design spec."""

    def test_ambiguity_threshold(self) -> None:
        assert AMBIGUITY_THRESHOLD == 0.3

    def test_multi_domain_threshold(self) -> None:
        assert MULTI_DOMAIN_THRESHOLD == 0.3

    def test_hyde_threshold(self) -> None:
        assert HYDE_THRESHOLD == 0.5


# ---------------------------------------------------------------------------
# classify() — single-domain queries
# ---------------------------------------------------------------------------


class TestClassifySingleDomain:
    """Tests for single-domain classification results."""

    def test_product_query(self) -> None:
        router, _ = _make_router('{"product": 0.9, "policy": 0.05, "customer": 0.05}')
        result = router.classify("What materials are the Airlift leggings made of?")

        assert isinstance(result, IntentClassification)
        assert result.primary_domain == "product"
        assert result.domains["product"] == 0.9
        assert result.is_ambiguous is False
        assert result.is_multi_domain is False

    def test_policy_query(self) -> None:
        router, _ = _make_router('{"product": 0.05, "policy": 0.85, "customer": 0.1}')
        result = router.classify("What is the return window for sale items?")

        assert result.primary_domain == "policy"
        assert result.domains["policy"] == 0.85
        assert result.is_ambiguous is False
        assert result.is_multi_domain is False

    def test_customer_query(self) -> None:
        router, _ = _make_router('{"product": 0.05, "policy": 0.05, "customer": 0.9}')
        result = router.classify("What did Sarah Chen order last month?")

        assert result.primary_domain == "customer"
        assert result.domains["customer"] == 0.9
        assert result.is_ambiguous is False


# ---------------------------------------------------------------------------
# classify() — ambiguity detection (R5.3)
# ---------------------------------------------------------------------------


class TestClassifyAmbiguity:
    """Tests for ambiguity detection when max confidence < 0.3."""

    def test_all_scores_below_threshold(self) -> None:
        router, _ = _make_router('{"product": 0.1, "policy": 0.1, "customer": 0.1}')
        result = router.classify("Tell me something")

        assert result.is_ambiguous is True

    def test_all_scores_zero(self) -> None:
        router, _ = _make_router('{"product": 0.0, "policy": 0.0, "customer": 0.0}')
        result = router.classify("Hello")

        assert result.is_ambiguous is True

    def test_max_score_exactly_at_threshold_is_not_ambiguous(self) -> None:
        """Score == 0.3 is NOT below 0.3, so is_ambiguous should be False."""
        router, _ = _make_router('{"product": 0.3, "policy": 0.2, "customer": 0.1}')
        result = router.classify("test")

        assert result.is_ambiguous is False

    def test_max_score_just_below_threshold(self) -> None:
        router, _ = _make_router('{"product": 0.29, "policy": 0.2, "customer": 0.1}')
        result = router.classify("test")

        assert result.is_ambiguous is True


# ---------------------------------------------------------------------------
# classify() — multi-domain detection (R5.4)
# ---------------------------------------------------------------------------


class TestClassifyMultiDomain:
    """Tests for multi-domain detection when 2+ domains > 0.3."""

    def test_two_domains_above_threshold(self) -> None:
        router, _ = _make_router('{"product": 0.5, "policy": 0.4, "customer": 0.1}')
        result = router.classify("Return policy for the leggings I bought")

        assert result.is_multi_domain is True

    def test_three_domains_above_threshold(self) -> None:
        router, _ = _make_router('{"product": 0.4, "policy": 0.35, "customer": 0.35}')
        result = router.classify("complex query")

        assert result.is_multi_domain is True

    def test_only_one_domain_above_threshold(self) -> None:
        router, _ = _make_router('{"product": 0.8, "policy": 0.1, "customer": 0.1}')
        result = router.classify("product query")

        assert result.is_multi_domain is False

    def test_scores_exactly_at_threshold_not_multi_domain(self) -> None:
        """Scores at exactly 0.3 are NOT above 0.3, so not multi-domain."""
        router, _ = _make_router('{"product": 0.5, "policy": 0.3, "customer": 0.2}')
        result = router.classify("test")

        assert result.is_multi_domain is False


# ---------------------------------------------------------------------------
# classify() — LLM interaction
# ---------------------------------------------------------------------------


class TestClassifyLLMInteraction:
    """Tests for how classify() interacts with the LLM client."""

    def test_passes_query_as_prompt(self) -> None:
        router, mock_llm = _make_router('{"product": 0.5, "policy": 0.3, "customer": 0.2}')
        router.classify("What size should I get?")

        mock_llm.classify.assert_called_once()
        call_kwargs = mock_llm.classify.call_args
        assert call_kwargs.kwargs["prompt"] == "What size should I get?"

    def test_passes_system_prompt(self) -> None:
        router, mock_llm = _make_router('{"product": 0.5, "policy": 0.3, "customer": 0.2}')
        router.classify("test query")

        call_kwargs = mock_llm.classify.call_args
        assert call_kwargs.kwargs["system"] == _CLASSIFICATION_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# classify() — error handling / graceful fallback
# ---------------------------------------------------------------------------


class TestClassifyErrorHandling:
    """Tests for graceful error handling in classify()."""

    def test_llm_exception_returns_safe_default(self) -> None:
        mock_llm = MagicMock()
        mock_llm.classify.side_effect = RuntimeError("API timeout")
        router = IntentRouter(mock_llm)

        result = router.classify("test")

        assert result.is_ambiguous is True
        assert result.domains == {"product": 0.0, "policy": 0.0, "customer": 0.0}

    def test_invalid_json_returns_safe_default(self) -> None:
        router, _ = _make_router("This is not JSON at all")
        result = router.classify("test")

        assert result.is_ambiguous is True
        assert result.domains == {"product": 0.0, "policy": 0.0, "customer": 0.0}

    def test_json_with_markdown_fences(self) -> None:
        response = '```json\n{"product": 0.7, "policy": 0.2, "customer": 0.1}\n```'
        router, _ = _make_router(response)
        result = router.classify("test")

        assert result.domains["product"] == 0.7
        assert result.is_ambiguous is False

    def test_missing_domain_defaults_to_zero(self) -> None:
        router, _ = _make_router('{"product": 0.9}')
        result = router.classify("test")

        assert result.domains["product"] == 0.9
        assert result.domains["policy"] == 0.0
        assert result.domains["customer"] == 0.0

    def test_extra_domains_ignored(self) -> None:
        router, _ = _make_router(
            '{"product": 0.5, "policy": 0.3, "customer": 0.1, "unknown": 0.9}'
        )
        result = router.classify("test")

        assert "unknown" not in result.domains
        assert len(result.domains) == 3

    def test_scores_clamped_to_valid_range(self) -> None:
        router, _ = _make_router('{"product": 1.5, "policy": -0.2, "customer": 0.3}')
        result = router.classify("test")

        assert result.domains["product"] == 1.0
        assert result.domains["policy"] == 0.0
        assert result.domains["customer"] == 0.3

    def test_non_numeric_score_defaults_to_zero(self) -> None:
        router, _ = _make_router('{"product": "high", "policy": 0.3, "customer": 0.1}')
        result = router.classify("test")

        assert result.domains["product"] == 0.0

    def test_json_array_returns_safe_default(self) -> None:
        router, _ = _make_router('[0.5, 0.3, 0.2]')
        result = router.classify("test")

        assert result.is_ambiguous is True
        assert result.domains == {"product": 0.0, "policy": 0.0, "customer": 0.0}
