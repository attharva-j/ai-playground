"""Unit tests for the scope guard module.

Requirements: 11.1, 11.2, 11.3
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.models import IntentClassification, ScopeDecision
from src.query.scope_guard import (
    ScopeGuard,
    _REFUSAL_MESSAGE,
    _SCOPE_EVALUATION_SYSTEM_PROMPT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_guard(classify_return: str) -> tuple[ScopeGuard, MagicMock]:
    """Create a ScopeGuard with a mocked LLMClient returning *classify_return*."""
    mock_llm = MagicMock()
    mock_llm.classify.return_value = classify_return
    return ScopeGuard(mock_llm), mock_llm


def _ambiguous_classification() -> IntentClassification:
    """Return an ambiguous IntentClassification (all scores < 0.3)."""
    return IntentClassification(
        domains={"product": 0.1, "policy": 0.1, "customer": 0.1},
        is_ambiguous=True,
        is_multi_domain=False,
        primary_domain="product",
    )


# ---------------------------------------------------------------------------
# evaluate() — out-of-scope refusal (R11.2)
# ---------------------------------------------------------------------------


class TestOutOfScope:
    """Tests for out-of-scope query detection and polite refusal."""

    def test_out_of_scope_returns_refusal(self) -> None:
        """R11.2: Out-of-scope queries get a polite refusal message."""
        response = (
            '{"is_in_scope": false, '
            '"reason": "Query is about cooking recipes, unrelated to ALO Yoga.", '
            '"uncertainty_note": null}'
        )
        guard, _ = _make_guard(response)
        result = guard.evaluate("How do I make pasta?", _ambiguous_classification())

        assert result.is_in_scope is False
        assert result.suggested_response == _REFUSAL_MESSAGE
        assert result.uncertainty_note is None
        assert "cooking" in result.reason

    def test_out_of_scope_refusal_is_polite(self) -> None:
        """R11.2: The refusal message should be polite and helpful."""
        assert "appreciate" in _REFUSAL_MESSAGE.lower() or "help" in _REFUSAL_MESSAGE.lower()
        assert "ALO Yoga" in _REFUSAL_MESSAGE

    def test_out_of_scope_ignores_llm_uncertainty_note(self) -> None:
        """Out-of-scope decisions should not carry an uncertainty_note."""
        response = (
            '{"is_in_scope": false, '
            '"reason": "Not about ALO Yoga.", '
            '"uncertainty_note": "Some note from LLM"}'
        )
        guard, _ = _make_guard(response)
        result = guard.evaluate("What is the weather?", _ambiguous_classification())

        assert result.is_in_scope is False
        assert result.uncertainty_note is None
        assert result.suggested_response == _REFUSAL_MESSAGE


# ---------------------------------------------------------------------------
# evaluate() — in-scope with uncertainty note (R11.3)
# ---------------------------------------------------------------------------


class TestInScopeWithUncertainty:
    """Tests for in-scope but ambiguous queries with uncertainty notes."""

    def test_in_scope_ambiguous_has_uncertainty_note(self) -> None:
        """R11.3: Ambiguous in-scope queries get an uncertainty_note."""
        response = (
            '{"is_in_scope": true, '
            '"reason": "Query may relate to ALO Yoga product materials.", '
            '"uncertainty_note": "This query is ambiguous — it may relate to ALO Yoga product materials, but the specific product is unclear."}'
        )
        guard, _ = _make_guard(response)
        result = guard.evaluate("What material is this?", _ambiguous_classification())

        assert result.is_in_scope is True
        assert result.uncertainty_note is not None
        assert "ambiguous" in result.uncertainty_note.lower()
        assert result.suggested_response is None

    def test_in_scope_ambiguous_preserves_reason(self) -> None:
        """The reason field should be preserved from the LLM response."""
        response = (
            '{"is_in_scope": true, '
            '"reason": "Could be about ALO Yoga sizing.", '
            '"uncertainty_note": "Unclear which product."}'
        )
        guard, _ = _make_guard(response)
        result = guard.evaluate("What size?", _ambiguous_classification())

        assert "sizing" in result.reason.lower()


# ---------------------------------------------------------------------------
# evaluate() — normal in-scope (no uncertainty)
# ---------------------------------------------------------------------------


class TestNormalInScope:
    """Tests for clearly in-scope queries with no ambiguity."""

    def test_normal_in_scope_no_uncertainty(self) -> None:
        """Normal in-scope queries have no uncertainty_note or suggested_response."""
        response = (
            '{"is_in_scope": true, '
            '"reason": "Query is about yoga leggings sizing.", '
            '"uncertainty_note": null}'
        )
        guard, _ = _make_guard(response)
        result = guard.evaluate("What sizes do the Airlift leggings come in?", _ambiguous_classification())

        assert result.is_in_scope is True
        assert result.uncertainty_note is None
        assert result.suggested_response is None
        assert result.reason != ""


# ---------------------------------------------------------------------------
# evaluate() — LLM interaction
# ---------------------------------------------------------------------------


class TestLLMInteraction:
    """Tests for how evaluate() interacts with the LLM client."""

    def test_passes_query_as_prompt(self) -> None:
        response = '{"is_in_scope": true, "reason": "ok", "uncertainty_note": null}'
        guard, mock_llm = _make_guard(response)
        guard.evaluate("What is the return policy?", _ambiguous_classification())

        mock_llm.classify.assert_called_once()
        call_kwargs = mock_llm.classify.call_args
        assert call_kwargs.kwargs["prompt"] == "What is the return policy?"

    def test_passes_system_prompt(self) -> None:
        response = '{"is_in_scope": true, "reason": "ok", "uncertainty_note": null}'
        guard, mock_llm = _make_guard(response)
        guard.evaluate("test query", _ambiguous_classification())

        call_kwargs = mock_llm.classify.call_args
        assert call_kwargs.kwargs["system"] == _SCOPE_EVALUATION_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# evaluate() — error handling / graceful fallback
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for graceful error handling — defaults to in-scope with uncertainty."""

    def test_llm_exception_returns_safe_fallback(self) -> None:
        """LLM failures default to in-scope with uncertainty note (safer than refusing)."""
        mock_llm = MagicMock()
        mock_llm.classify.side_effect = RuntimeError("API timeout")
        guard = ScopeGuard(mock_llm)

        result = guard.evaluate("test", _ambiguous_classification())

        assert result.is_in_scope is True
        assert result.uncertainty_note is not None
        assert result.suggested_response is None

    def test_invalid_json_returns_safe_fallback(self) -> None:
        guard, _ = _make_guard("This is not JSON at all")
        result = guard.evaluate("test", _ambiguous_classification())

        assert result.is_in_scope is True
        assert result.uncertainty_note is not None

    def test_json_with_markdown_fences(self) -> None:
        response = '```json\n{"is_in_scope": false, "reason": "Not ALO Yoga.", "uncertainty_note": null}\n```'
        guard, _ = _make_guard(response)
        result = guard.evaluate("test", _ambiguous_classification())

        assert result.is_in_scope is False
        assert result.suggested_response == _REFUSAL_MESSAGE

    def test_missing_is_in_scope_returns_safe_fallback(self) -> None:
        guard, _ = _make_guard('{"reason": "some reason", "uncertainty_note": null}')
        result = guard.evaluate("test", _ambiguous_classification())

        assert result.is_in_scope is True
        assert result.uncertainty_note is not None

    def test_non_bool_is_in_scope_returns_safe_fallback(self) -> None:
        guard, _ = _make_guard('{"is_in_scope": "yes", "reason": "ok", "uncertainty_note": null}')
        result = guard.evaluate("test", _ambiguous_classification())

        assert result.is_in_scope is True
        assert result.uncertainty_note is not None

    def test_json_array_returns_safe_fallback(self) -> None:
        guard, _ = _make_guard('[true, "reason", null]')
        result = guard.evaluate("test", _ambiguous_classification())

        assert result.is_in_scope is True
        assert result.uncertainty_note is not None

    def test_missing_reason_defaults_to_empty_string(self) -> None:
        guard, _ = _make_guard('{"is_in_scope": true, "uncertainty_note": null}')
        result = guard.evaluate("test", _ambiguous_classification())

        assert result.is_in_scope is True
        assert result.reason == ""

    def test_missing_uncertainty_note_defaults_to_none(self) -> None:
        guard, _ = _make_guard('{"is_in_scope": true, "reason": "ok"}')
        result = guard.evaluate("test", _ambiguous_classification())

        assert result.is_in_scope is True
        assert result.uncertainty_note is None


# ---------------------------------------------------------------------------
# ScopeDecision dataclass — three outcome verification
# ---------------------------------------------------------------------------


class TestScopeDecisionOutcomes:
    """Verify the three possible ScopeDecision outcomes are distinct."""

    def test_out_of_scope_outcome(self) -> None:
        decision = ScopeDecision(
            is_in_scope=False,
            reason="Not about ALO Yoga",
            suggested_response=_REFUSAL_MESSAGE,
            uncertainty_note=None,
        )
        assert decision.is_in_scope is False
        assert decision.suggested_response is not None
        assert decision.uncertainty_note is None

    def test_in_scope_ambiguous_outcome(self) -> None:
        decision = ScopeDecision(
            is_in_scope=True,
            reason="Possibly about products",
            suggested_response=None,
            uncertainty_note="The query is ambiguous.",
        )
        assert decision.is_in_scope is True
        assert decision.suggested_response is None
        assert decision.uncertainty_note is not None

    def test_normal_in_scope_outcome(self) -> None:
        decision = ScopeDecision(
            is_in_scope=True,
            reason="About ALO Yoga leggings",
            suggested_response=None,
            uncertainty_note=None,
        )
        assert decision.is_in_scope is True
        assert decision.suggested_response is None
        assert decision.uncertainty_note is None
