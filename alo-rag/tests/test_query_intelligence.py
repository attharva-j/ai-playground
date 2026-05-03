"""Integration-level unit tests for the query intelligence layer.

Verifies cross-component behaviors across the query intelligence layer:
- IntentRouter classifies product, policy, customer, and multi-domain queries
- Ambiguity detection when all scores < 0.3
- HyDE activation logic (only for policy queries with confidence > 0.5)
- QueryDecomposer splits multi-domain queries correctly
- ScopeGuard returns refusal for out-of-scope and uncertainty note for ambiguous in-scope

Requirements: 5.1, 5.3, 5.4, 6.1, 7.1, 11.1, 11.2, 11.3
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, call

import pytest

from src.generation.llm_client import LLMClient
from src.models import IntentClassification, ScopeDecision, SubQuery
from src.query.decomposer import QueryDecomposer
from src.query.hyde import HyDEModule
from src.query.intent_router import (
    AMBIGUITY_THRESHOLD,
    HYDE_THRESHOLD,
    MULTI_DOMAIN_THRESHOLD,
    IntentRouter,
)
from src.query.scope_guard import ScopeGuard, _REFUSAL_MESSAGE


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _mock_llm(classify_return: str = "", generate_return: str = "") -> MagicMock:
    """Create a MagicMock LLMClient with configurable return values."""
    mock = MagicMock(spec=LLMClient)
    mock.classify.return_value = classify_return
    mock.generate.return_value = generate_return
    return mock


def _mock_embedder(embed_return: list[float] | None = None) -> MagicMock:
    """Create a MagicMock EmbeddingService."""
    mock = MagicMock()
    mock.embed_single.return_value = embed_return or [0.1, 0.2, 0.3]
    return mock


def _build_classification(
    domains: dict[str, float],
    primary_domain: str | None = None,
) -> IntentClassification:
    """Build an IntentClassification from domain scores, computing flags."""
    max_score = max(domains.values()) if domains else 0.0
    if primary_domain is None:
        primary_domain = max(domains, key=domains.get) if domains else "product"  # type: ignore[arg-type]
    high_scoring = [d for d, s in domains.items() if s > MULTI_DOMAIN_THRESHOLD]
    return IntentClassification(
        domains=domains,
        is_ambiguous=max_score < AMBIGUITY_THRESHOLD,
        is_multi_domain=len(high_scoring) >= 2,
        primary_domain=primary_domain,
    )


# ===========================================================================
# 1. IntentRouter — domain classification (R5.1)
# ===========================================================================


class TestIntentRouterDomainClassification:
    """IntentRouter classifies product, policy, customer, and multi-domain queries."""

    def test_classifies_product_query(self) -> None:
        """R5.1: Product queries get high product confidence."""
        llm = _mock_llm(classify_return='{"product": 0.9, "policy": 0.05, "customer": 0.05}')
        router = IntentRouter(llm)

        result = router.classify("What materials are the Airlift leggings made of?")

        assert result.primary_domain == "product"
        assert result.domains["product"] == pytest.approx(0.9)
        assert result.is_ambiguous is False
        assert result.is_multi_domain is False

    def test_classifies_policy_query(self) -> None:
        """R5.1: Policy queries get high policy confidence."""
        llm = _mock_llm(classify_return='{"product": 0.05, "policy": 0.85, "customer": 0.1}')
        router = IntentRouter(llm)

        result = router.classify("What is the return window for sale items?")

        assert result.primary_domain == "policy"
        assert result.domains["policy"] == pytest.approx(0.85)
        assert result.is_ambiguous is False

    def test_classifies_customer_query(self) -> None:
        """R5.1: Customer queries get high customer confidence."""
        llm = _mock_llm(classify_return='{"product": 0.05, "policy": 0.05, "customer": 0.9}')
        router = IntentRouter(llm)

        result = router.classify("What did Sarah Chen order last month?")

        assert result.primary_domain == "customer"
        assert result.domains["customer"] == pytest.approx(0.9)
        assert result.is_ambiguous is False

    def test_classifies_multi_domain_query(self) -> None:
        """R5.4: Multi-domain queries have 2+ domains above threshold."""
        llm = _mock_llm(classify_return='{"product": 0.5, "policy": 0.4, "customer": 0.1}')
        router = IntentRouter(llm)

        result = router.classify("Return policy for the leggings I bought")

        assert result.is_multi_domain is True
        assert result.domains["product"] > MULTI_DOMAIN_THRESHOLD
        assert result.domains["policy"] > MULTI_DOMAIN_THRESHOLD

    def test_returns_all_three_domain_scores(self) -> None:
        """R5.1: Classification always returns scores for all three domains."""
        llm = _mock_llm(classify_return='{"product": 0.7, "policy": 0.2, "customer": 0.1}')
        router = IntentRouter(llm)

        result = router.classify("test query")

        assert set(result.domains.keys()) == {"product", "policy", "customer"}
        assert all(0.0 <= score <= 1.0 for score in result.domains.values())


# ===========================================================================
# 2. IntentRouter — ambiguity detection (R5.3)
# ===========================================================================


class TestIntentRouterAmbiguityDetection:
    """Ambiguity detection when all domain confidence scores < 0.3."""

    def test_all_scores_below_threshold_is_ambiguous(self) -> None:
        """R5.3: When max confidence < 0.3, query is flagged as ambiguous."""
        llm = _mock_llm(classify_return='{"product": 0.1, "policy": 0.15, "customer": 0.05}')
        router = IntentRouter(llm)

        result = router.classify("Tell me something interesting")

        assert result.is_ambiguous is True

    def test_all_scores_zero_is_ambiguous(self) -> None:
        """R5.3: Zero scores across all domains → ambiguous."""
        llm = _mock_llm(classify_return='{"product": 0.0, "policy": 0.0, "customer": 0.0}')
        router = IntentRouter(llm)

        result = router.classify("Hello")

        assert result.is_ambiguous is True

    def test_one_score_at_threshold_is_not_ambiguous(self) -> None:
        """Score == 0.3 is not below 0.3, so is_ambiguous should be False."""
        llm = _mock_llm(classify_return='{"product": 0.3, "policy": 0.2, "customer": 0.1}')
        router = IntentRouter(llm)

        result = router.classify("test")

        assert result.is_ambiguous is False

    def test_scores_just_below_threshold_is_ambiguous(self) -> None:
        """R5.3: Scores at 0.29 (just below 0.3) → ambiguous."""
        llm = _mock_llm(classify_return='{"product": 0.29, "policy": 0.29, "customer": 0.29}')
        router = IntentRouter(llm)

        result = router.classify("vague question")

        assert result.is_ambiguous is True

    def test_llm_failure_produces_ambiguous_classification(self) -> None:
        """When LLM fails, safe default is all-zero scores → ambiguous."""
        llm = _mock_llm()
        llm.classify.side_effect = RuntimeError("API timeout")
        router = IntentRouter(llm)

        result = router.classify("test")

        assert result.is_ambiguous is True
        assert result.domains == {"product": 0.0, "policy": 0.0, "customer": 0.0}


# ===========================================================================
# 3. HyDE activation logic (R6.1)
# ===========================================================================


class TestHyDEActivationLogic:
    """HyDE should activate only for policy queries with confidence > 0.5.

    The HyDEModule itself doesn't decide when to activate — that's the
    pipeline's job based on IntentRouter output. These tests verify the
    threshold logic and that HyDE produces correct outputs when called.
    """

    def test_hyde_threshold_matches_design(self) -> None:
        """R6.1: HYDE_THRESHOLD is 0.5 per the design spec."""
        assert HYDE_THRESHOLD == 0.5

    def test_policy_above_threshold_should_activate_hyde(self) -> None:
        """R6.1: Policy confidence > 0.5 → HyDE should be activated."""
        llm = _mock_llm(classify_return='{"product": 0.1, "policy": 0.7, "customer": 0.2}')
        router = IntentRouter(llm)

        classification = router.classify("What is the return window for sale items?")

        # Pipeline would check this condition to activate HyDE
        should_activate = (
            classification.primary_domain == "policy"
            and classification.domains.get("policy", 0.0) > HYDE_THRESHOLD
        )
        assert should_activate is True

    def test_policy_below_threshold_should_not_activate_hyde(self) -> None:
        """R6.1: Policy confidence <= 0.5 → HyDE should NOT be activated."""
        llm = _mock_llm(classify_return='{"product": 0.3, "policy": 0.4, "customer": 0.3}')
        router = IntentRouter(llm)

        classification = router.classify("Something about policies maybe?")

        should_activate = (
            classification.primary_domain == "policy"
            and classification.domains.get("policy", 0.0) > HYDE_THRESHOLD
        )
        assert should_activate is False

    def test_product_query_should_not_activate_hyde(self) -> None:
        """R6.1: Non-policy queries should not activate HyDE regardless of score."""
        llm = _mock_llm(classify_return='{"product": 0.9, "policy": 0.05, "customer": 0.05}')
        router = IntentRouter(llm)

        classification = router.classify("What are the Airlift leggings made of?")

        should_activate = (
            classification.primary_domain == "policy"
            and classification.domains.get("policy", 0.0) > HYDE_THRESHOLD
        )
        assert should_activate is False

    def test_customer_query_should_not_activate_hyde(self) -> None:
        """R6.1: Customer queries should not activate HyDE."""
        llm = _mock_llm(classify_return='{"product": 0.05, "policy": 0.05, "customer": 0.9}')
        router = IntentRouter(llm)

        classification = router.classify("What did I order last month?")

        should_activate = (
            classification.primary_domain == "policy"
            and classification.domains.get("policy", 0.0) > HYDE_THRESHOLD
        )
        assert should_activate is False

    def test_policy_at_exactly_threshold_should_not_activate(self) -> None:
        """R6.1: Policy confidence == 0.5 is NOT above 0.5 → no HyDE."""
        llm = _mock_llm(classify_return='{"product": 0.3, "policy": 0.5, "customer": 0.2}')
        router = IntentRouter(llm)

        classification = router.classify("test")

        should_activate = (
            classification.primary_domain == "policy"
            and classification.domains.get("policy", 0.0) > HYDE_THRESHOLD
        )
        assert should_activate is False

    def test_hyde_process_returns_embedding(self) -> None:
        """R6.2: When activated, HyDE returns an embedding of the hypothetical answer."""
        llm = _mock_llm(classify_return="Returns are accepted within 30 days of purchase.")
        embedder = _mock_embedder(embed_return=[0.5, 0.6, 0.7])
        hyde = HyDEModule(llm_client=llm, embedding_service=embedder)

        embedding = hyde.process("What is the return window?")

        assert embedding == [0.5, 0.6, 0.7]
        # Verify the hypothetical was embedded, not the original query
        embedder.embed_single.assert_called_once_with(
            "Returns are accepted within 30 days of purchase."
        )

    def test_hyde_embeds_hypothetical_not_query(self) -> None:
        """R6.2: HyDE embeds the hypothetical answer, not the raw query."""
        llm = _mock_llm(classify_return="Free shipping on orders over $75.")
        embedder = _mock_embedder()
        hyde = HyDEModule(llm_client=llm, embedding_service=embedder)

        hyde.process("Do you offer free shipping?")

        # The embedder should receive the hypothetical, not the query
        embed_arg = embedder.embed_single.call_args[0][0]
        assert embed_arg == "Free shipping on orders over $75."
        assert embed_arg != "Do you offer free shipping?"


# ===========================================================================
# 4. QueryDecomposer — multi-domain splitting (R7.1)
# ===========================================================================


class TestQueryDecomposerMultiDomain:
    """QueryDecomposer splits multi-domain queries correctly."""

    def test_splits_two_domain_query(self) -> None:
        """R7.1: Multi-domain query is split into domain-specific sub-queries."""
        llm_response = json.dumps([
            {"text": "What is the return policy for sale items?", "domain": "policy"},
            {"text": "What leggings did I buy last month?", "domain": "customer"},
        ])
        llm = _mock_llm(classify_return=llm_response)
        decomposer = QueryDecomposer(llm)
        classification = _build_classification(
            {"product": 0.1, "policy": 0.5, "customer": 0.4},
        )

        result = decomposer.decompose(
            "What's the return policy for the leggings I bought last month?",
            classification,
        )

        assert len(result) == 2
        domains = {sq.target_domain for sq in result}
        assert domains == {"policy", "customer"}

    def test_splits_three_domain_query(self) -> None:
        """R7.1: Three-domain query produces three sub-queries."""
        llm_response = json.dumps([
            {"text": "What are the Airlift leggings made of?", "domain": "product"},
            {"text": "What is the return policy?", "domain": "policy"},
            {"text": "What did I order last month?", "domain": "customer"},
        ])
        llm = _mock_llm(classify_return=llm_response)
        decomposer = QueryDecomposer(llm)
        classification = _build_classification(
            {"product": 0.4, "policy": 0.35, "customer": 0.35},
        )

        result = decomposer.decompose("complex multi-domain query", classification)

        assert len(result) == 3
        domains = {sq.target_domain for sq in result}
        assert domains == {"product", "policy", "customer"}

    def test_single_domain_query_not_decomposed(self) -> None:
        """R7.1: Single-domain queries are not decomposed (no LLM call)."""
        llm = _mock_llm()
        decomposer = QueryDecomposer(llm)
        classification = _build_classification(
            {"product": 0.9, "policy": 0.05, "customer": 0.05},
        )

        result = decomposer.decompose("What are the leggings made of?", classification)

        assert len(result) == 1
        assert result[0].target_domain == "product"
        assert result[0].text == "What are the leggings made of?"
        llm.classify.assert_not_called()

    def test_preserves_original_query_in_sub_queries(self) -> None:
        """R7.1: Each sub-query retains a reference to the original query."""
        llm_response = json.dumps([
            {"text": "Sub-query about policy", "domain": "policy"},
            {"text": "Sub-query about customer", "domain": "customer"},
        ])
        llm = _mock_llm(classify_return=llm_response)
        decomposer = QueryDecomposer(llm)
        classification = _build_classification(
            {"product": 0.1, "policy": 0.5, "customer": 0.4},
        )

        original = "What's the return policy for my recent order?"
        result = decomposer.decompose(original, classification)

        for sq in result:
            assert sq.original_query == original

    def test_ambiguous_query_returns_single_sub_query(self) -> None:
        """Ambiguous queries (no domain above threshold) return one sub-query."""
        llm = _mock_llm()
        decomposer = QueryDecomposer(llm)
        classification = _build_classification(
            {"product": 0.1, "policy": 0.1, "customer": 0.1},
        )

        result = decomposer.decompose("Hello there", classification)

        assert len(result) == 1
        assert result[0].target_domain == classification.primary_domain
        llm.classify.assert_not_called()

    def test_decomposition_fallback_on_llm_failure(self) -> None:
        """R7.1: LLM failure falls back to one sub-query per relevant domain."""
        llm = _mock_llm()
        llm.classify.side_effect = RuntimeError("API error")
        decomposer = QueryDecomposer(llm)
        classification = _build_classification(
            {"product": 0.5, "policy": 0.4, "customer": 0.1},
        )

        result = decomposer.decompose("test query", classification)

        assert len(result) == 2
        domains = {sq.target_domain for sq in result}
        assert domains == {"product", "policy"}
        assert all(sq.text == "test query" for sq in result)


# ===========================================================================
# 5. ScopeGuard — out-of-scope refusal (R11.1, R11.2)
# ===========================================================================


class TestScopeGuardOutOfScope:
    """ScopeGuard returns polite refusal for out-of-scope queries."""

    def test_out_of_scope_returns_refusal_message(self) -> None:
        """R11.2: Out-of-scope queries get a polite refusal."""
        response = json.dumps({
            "is_in_scope": False,
            "reason": "Query is about cooking recipes, unrelated to ALO Yoga.",
            "uncertainty_note": None,
        })
        llm = _mock_llm(classify_return=response)
        guard = ScopeGuard(llm)
        classification = _build_classification(
            {"product": 0.1, "policy": 0.1, "customer": 0.1},
        )

        result = guard.evaluate("How do I make pasta?", classification)

        assert result.is_in_scope is False
        assert result.suggested_response is not None
        assert result.suggested_response == _REFUSAL_MESSAGE
        assert result.uncertainty_note is None

    def test_refusal_message_is_polite_and_helpful(self) -> None:
        """R11.2: The refusal message should be polite and mention ALO Yoga."""
        assert "ALO Yoga" in _REFUSAL_MESSAGE
        # Should mention what the system CAN help with
        assert "product" in _REFUSAL_MESSAGE.lower() or "policies" in _REFUSAL_MESSAGE.lower()

    def test_out_of_scope_does_not_carry_uncertainty_note(self) -> None:
        """R11.2: Out-of-scope decisions should have no uncertainty_note."""
        response = json.dumps({
            "is_in_scope": False,
            "reason": "Not about ALO Yoga.",
            "uncertainty_note": "Some note the LLM added",
        })
        llm = _mock_llm(classify_return=response)
        guard = ScopeGuard(llm)
        classification = _build_classification(
            {"product": 0.05, "policy": 0.05, "customer": 0.05},
        )

        result = guard.evaluate("What is the weather?", classification)

        assert result.is_in_scope is False
        assert result.uncertainty_note is None


# ===========================================================================
# 6. ScopeGuard — in-scope with uncertainty (R11.3)
# ===========================================================================


class TestScopeGuardInScopeAmbiguous:
    """ScopeGuard returns uncertainty note for ambiguous in-scope queries."""

    def test_ambiguous_in_scope_has_uncertainty_note(self) -> None:
        """R11.3: Ambiguous in-scope queries get an uncertainty_note."""
        response = json.dumps({
            "is_in_scope": True,
            "reason": "Query may relate to ALO Yoga product materials.",
            "uncertainty_note": "This query is ambiguous — the specific product is unclear.",
        })
        llm = _mock_llm(classify_return=response)
        guard = ScopeGuard(llm)
        classification = _build_classification(
            {"product": 0.2, "policy": 0.1, "customer": 0.1},
        )

        result = guard.evaluate("What material is this?", classification)

        assert result.is_in_scope is True
        assert result.uncertainty_note is not None
        assert len(result.uncertainty_note) > 0
        assert result.suggested_response is None

    def test_clear_in_scope_has_no_uncertainty_note(self) -> None:
        """R11.3: Clearly in-scope queries have no uncertainty_note."""
        response = json.dumps({
            "is_in_scope": True,
            "reason": "Query is about yoga leggings sizing.",
            "uncertainty_note": None,
        })
        llm = _mock_llm(classify_return=response)
        guard = ScopeGuard(llm)
        classification = _build_classification(
            {"product": 0.2, "policy": 0.1, "customer": 0.1},
        )

        result = guard.evaluate("What sizes do the Airlift leggings come in?", classification)

        assert result.is_in_scope is True
        assert result.uncertainty_note is None
        assert result.suggested_response is None

    def test_llm_failure_defaults_to_in_scope_with_uncertainty(self) -> None:
        """R11.1: LLM failure defaults to in-scope with uncertainty (safer than refusing)."""
        llm = _mock_llm()
        llm.classify.side_effect = RuntimeError("API timeout")
        guard = ScopeGuard(llm)
        classification = _build_classification(
            {"product": 0.1, "policy": 0.1, "customer": 0.1},
        )

        result = guard.evaluate("test", classification)

        assert result.is_in_scope is True
        assert result.uncertainty_note is not None
        assert result.suggested_response is None


# ===========================================================================
# 7. End-to-end flow: IntentRouter → conditional HyDE / Decomposer / ScopeGuard
# ===========================================================================


class TestQueryIntelligenceFlow:
    """Integration tests verifying the routing logic across components.

    These tests simulate the pipeline's decision flow:
    1. IntentRouter classifies the query
    2. Based on classification, the pipeline decides:
       - Ambiguous → ScopeGuard
       - Policy with high confidence → HyDE
       - Multi-domain → QueryDecomposer
    """

    def test_policy_query_flow_activates_hyde(self) -> None:
        """Policy query with high confidence → HyDE activation."""
        # Step 1: IntentRouter classifies as policy
        router_llm = _mock_llm(
            classify_return='{"product": 0.05, "policy": 0.8, "customer": 0.15}',
        )
        router = IntentRouter(router_llm)
        classification = router.classify("What is the return window for sale items?")

        assert classification.primary_domain == "policy"
        assert classification.domains["policy"] > HYDE_THRESHOLD

        # Step 2: HyDE generates and embeds hypothetical
        hyde_llm = _mock_llm(
            generate_return="Items purchased at 30% or more off are final sale and cannot be returned.",
        )
        embedder = _mock_embedder(embed_return=[0.4, 0.5, 0.6])
        hyde = HyDEModule(llm_client=hyde_llm, embedding_service=embedder)

        embedding = hyde.process("What is the return window for sale items?")

        assert isinstance(embedding, list)
        assert len(embedding) > 0

    def test_multi_domain_query_flow_decomposes(self) -> None:
        """Multi-domain query → QueryDecomposer splits into sub-queries."""
        # Step 1: IntentRouter classifies as multi-domain
        router_llm = _mock_llm(
            classify_return='{"product": 0.4, "policy": 0.5, "customer": 0.1}',
        )
        router = IntentRouter(router_llm)
        classification = router.classify(
            "What's the return policy for the Airlift leggings?"
        )

        assert classification.is_multi_domain is True

        # Step 2: QueryDecomposer splits the query
        decompose_response = json.dumps([
            {"text": "What is the return policy?", "domain": "policy"},
            {"text": "Tell me about the Airlift leggings.", "domain": "product"},
        ])
        decomposer_llm = _mock_llm(classify_return=decompose_response)
        decomposer = QueryDecomposer(decomposer_llm)

        sub_queries = decomposer.decompose(
            "What's the return policy for the Airlift leggings?",
            classification,
        )

        assert len(sub_queries) == 2
        domains = {sq.target_domain for sq in sub_queries}
        assert "policy" in domains
        assert "product" in domains

    def test_ambiguous_query_flow_triggers_scope_guard(self) -> None:
        """Ambiguous query → ScopeGuard evaluates scope."""
        # Step 1: IntentRouter classifies as ambiguous
        router_llm = _mock_llm(
            classify_return='{"product": 0.1, "policy": 0.1, "customer": 0.1}',
        )
        router = IntentRouter(router_llm)
        classification = router.classify("What is the meaning of life?")

        assert classification.is_ambiguous is True

        # Step 2: ScopeGuard evaluates — out-of-scope
        scope_response = json.dumps({
            "is_in_scope": False,
            "reason": "Query is philosophical, not about ALO Yoga.",
            "uncertainty_note": None,
        })
        guard_llm = _mock_llm(classify_return=scope_response)
        guard = ScopeGuard(guard_llm)

        decision = guard.evaluate("What is the meaning of life?", classification)

        assert decision.is_in_scope is False
        assert decision.suggested_response == _REFUSAL_MESSAGE

    def test_ambiguous_but_in_scope_flow(self) -> None:
        """Ambiguous query that's still in-scope → uncertainty note appended."""
        # Step 1: IntentRouter classifies as ambiguous
        router_llm = _mock_llm(
            classify_return='{"product": 0.2, "policy": 0.15, "customer": 0.1}',
        )
        router = IntentRouter(router_llm)
        classification = router.classify("What material is this?")

        assert classification.is_ambiguous is True

        # Step 2: ScopeGuard evaluates — in-scope but ambiguous
        scope_response = json.dumps({
            "is_in_scope": True,
            "reason": "Could relate to ALO Yoga product materials.",
            "uncertainty_note": "The query is ambiguous — the specific product is unclear.",
        })
        guard_llm = _mock_llm(classify_return=scope_response)
        guard = ScopeGuard(guard_llm)

        decision = guard.evaluate("What material is this?", classification)

        assert decision.is_in_scope is True
        assert decision.uncertainty_note is not None
        assert decision.suggested_response is None

    def test_clear_product_query_skips_hyde_and_decomposer(self) -> None:
        """Clear single-domain product query → no HyDE, no decomposition."""
        router_llm = _mock_llm(
            classify_return='{"product": 0.9, "policy": 0.05, "customer": 0.05}',
        )
        router = IntentRouter(router_llm)
        classification = router.classify("What sizes do the Airlift leggings come in?")

        # Should NOT activate HyDE
        should_activate_hyde = (
            classification.primary_domain == "policy"
            and classification.domains.get("policy", 0.0) > HYDE_THRESHOLD
        )
        assert should_activate_hyde is False

        # Should NOT decompose (single domain)
        assert classification.is_multi_domain is False
        assert classification.is_ambiguous is False

        # Decomposer returns single sub-query without LLM call
        decomposer_llm = _mock_llm()
        decomposer = QueryDecomposer(decomposer_llm)
        sub_queries = decomposer.decompose(
            "What sizes do the Airlift leggings come in?",
            classification,
        )

        assert len(sub_queries) == 1
        assert sub_queries[0].target_domain == "product"
        decomposer_llm.classify.assert_not_called()
