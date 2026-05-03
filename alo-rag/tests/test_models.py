"""Unit tests for core data models (src/models.py).

Covers:
- Dataclass instantiation and field defaults
- ChunkMetadata domain validation
- IntentClassification ambiguity and multi-domain logic

Requirements: 1.2, 2.3, 5.1
"""

from __future__ import annotations

import pytest

from src.models import (
    AnswerabilityDecision,
    Chunk,
    ChunkMetadata,
    Claim,
    CustomerProfile,
    EvalResult,
    FaithfulnessResult,
    FaithfulnessStatus,
    IntentClassification,
    Order,
    OrderItem,
    PipelineResult,
    RawDocument,
    RetrievedChunk,
    ScopeDecision,
    SubQuery,
    TestQuery,
    TraceLog,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_chunk(chunk_id: str = "c1", domain: str = "product") -> Chunk:
    """Create a minimal Chunk for use in composite model tests."""
    return Chunk(
        chunk_id=chunk_id,
        text="sample text",
        metadata=ChunkMetadata(domain=domain),
        source_document="source.json",
    )


def _make_intent(
    product: float = 0.8,
    policy: float = 0.1,
    customer: float = 0.1,
    *,
    is_ambiguous: bool = False,
    is_multi_domain: bool = False,
    primary_domain: str = "product",
) -> IntentClassification:
    return IntentClassification(
        domains={"product": product, "policy": policy, "customer": customer},
        is_ambiguous=is_ambiguous,
        is_multi_domain=is_multi_domain,
        primary_domain=primary_domain,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. Dataclass instantiation and field defaults
# ═══════════════════════════════════════════════════════════════════════════


class TestRawDocument:
    """RawDocument instantiation and defaults."""

    def test_create_with_required_fields(self) -> None:
        doc = RawDocument(content="hello", source="file.json", domain="product")
        assert doc.content == "hello"
        assert doc.source == "file.json"
        assert doc.domain == "product"

    def test_metadata_defaults_to_empty_dict(self) -> None:
        doc = RawDocument(content="", source="", domain="product")
        assert doc.metadata == {}

    def test_metadata_is_independent_across_instances(self) -> None:
        a = RawDocument(content="", source="", domain="product")
        b = RawDocument(content="", source="", domain="product")
        a.metadata["key"] = "value"
        assert "key" not in b.metadata

    def test_custom_metadata(self) -> None:
        doc = RawDocument(
            content="x", source="s", domain="policy", metadata={"k": "v"}
        )
        assert doc.metadata == {"k": "v"}


class TestChunkAndChunkMetadata:
    """Chunk / ChunkMetadata instantiation."""

    def test_chunk_metadata_defaults(self) -> None:
        meta = ChunkMetadata(domain="product")
        assert meta.product_id is None
        assert meta.category is None
        assert meta.fabric_type is None
        assert meta.policy_type is None
        assert meta.effective_date is None

    def test_chunk_metadata_product_fields(self) -> None:
        meta = ChunkMetadata(
            domain="product",
            product_id="ALO-001",
            category="leggings",
            fabric_type="Airlift",
        )
        assert meta.product_id == "ALO-001"
        assert meta.category == "leggings"
        assert meta.fabric_type == "Airlift"

    def test_chunk_metadata_policy_fields(self) -> None:
        meta = ChunkMetadata(
            domain="policy",
            policy_type="returns",
            effective_date="2024-01-01",
        )
        assert meta.policy_type == "returns"
        assert meta.effective_date == "2024-01-01"

    def test_chunk_creation(self) -> None:
        chunk = _make_chunk("c1", "product")
        assert chunk.chunk_id == "c1"
        assert chunk.text == "sample text"
        assert chunk.metadata.domain == "product"
        assert chunk.source_document == "source.json"


class TestRetrievedChunk:
    def test_create(self) -> None:
        rc = RetrievedChunk(chunk=_make_chunk(), score=0.95, source="dense")
        assert rc.score == 0.95
        assert rc.source == "dense"
        assert rc.chunk.chunk_id == "c1"


class TestCustomerModels:
    """OrderItem, Order, CustomerProfile instantiation and defaults."""

    def test_order_item(self) -> None:
        item = OrderItem(
            product_id="P1",
            product_name="Legging",
            quantity=1,
            price=118.0,
            size="S",
            was_discounted=False,
            discount_pct=0,
            final_sale=False,
        )
        assert item.product_id == "P1"
        assert item.was_discounted is False
        assert item.final_sale is False

    def test_order(self) -> None:
        item = OrderItem("P1", "Legging", 1, 118.0, "S", False, 0, False)
        order = Order(
            order_id="ORD-001",
            date="2024-01-15",
            items=[item],
            status="delivered",
            total=118.0,
        )
        assert len(order.items) == 1
        assert order.total == 118.0

    def test_customer_profile_defaults(self) -> None:
        cp = CustomerProfile(
            customer_id="C1", name="Alice", email="a@b.com"
        )
        assert cp.orders == []
        assert cp.loyalty_tier == ""

    def test_customer_profile_orders_independent(self) -> None:
        a = CustomerProfile(customer_id="C1", name="A", email="a@b.com")
        b = CustomerProfile(customer_id="C2", name="B", email="b@b.com")
        a.orders.append(
            Order("O1", "2024-01-01", [], "delivered", 0.0)
        )
        assert len(b.orders) == 0


class TestScopeDecision:
    def test_defaults(self) -> None:
        sd = ScopeDecision(is_in_scope=True, reason="clear product query")
        assert sd.suggested_response is None
        assert sd.uncertainty_note is None

    def test_out_of_scope(self) -> None:
        sd = ScopeDecision(
            is_in_scope=False,
            reason="weather query",
            suggested_response="I can only help with ALO Yoga topics.",
        )
        assert sd.is_in_scope is False
        assert sd.suggested_response is not None

    def test_in_scope_with_uncertainty(self) -> None:
        sd = ScopeDecision(
            is_in_scope=True,
            reason="ambiguous but plausible",
            uncertainty_note="This answer may be incomplete.",
        )
        assert sd.is_in_scope is True
        assert sd.uncertainty_note is not None


class TestSubQuery:
    def test_create(self) -> None:
        sq = SubQuery(
            text="return policy?",
            target_domain="policy",
            original_query="Can I return the leggings I bought?",
        )
        assert sq.target_domain == "policy"


class TestClaimAndFaithfulness:
    def test_claim_defaults(self) -> None:
        c = Claim(text="The legging is nylon.", supported=True)
        assert c.supporting_chunk_id is None

    def test_faithfulness_defaults(self) -> None:
        fr = FaithfulnessResult(score=1.0)
        assert fr.claims == []
        assert fr.unsupported_claims == []
        assert fr.regeneration_triggered is False
        assert fr.regenerated_answer is None

    def test_faithfulness_claims_independent(self) -> None:
        a = FaithfulnessResult(score=1.0)
        b = FaithfulnessResult(score=0.5)
        a.claims.append(Claim("x", True))
        assert len(b.claims) == 0


class TestTraceLog:
    def test_defaults(self) -> None:
        tl = TraceLog(
            query="test",
            timestamp="2024-01-01T00:00:00",
            intent_classification=_make_intent(),
            hyde_activated=False,
        )
        assert tl.hyde_hypothetical is None
        assert tl.decomposed_queries is None
        assert tl.scope_decision is None
        assert tl.answerability_decision is None
        assert tl.retrieval_results == []
        assert tl.reranking_scores == []
        assert tl.faithfulness_result is None
        assert tl.latency_ms == 0.0
        assert tl.stage_latencies == {}

    def test_mutable_defaults_independent(self) -> None:
        a = TraceLog("q", "t", _make_intent(), False)
        b = TraceLog("q", "t", _make_intent(), False)
        a.retrieval_results.append(
            RetrievedChunk(_make_chunk(), 0.9, "dense")
        )
        a.stage_latencies["intent"] = 10.0
        assert len(b.retrieval_results) == 0
        assert len(b.stage_latencies) == 0


class TestPipelineResult:
    def test_defaults(self) -> None:
        pr = PipelineResult(answer="hello")
        assert pr.chunks == []
        assert pr.trace is None
        assert pr.faithfulness_score is None
        assert pr.answerability_decision is None


class TestAnswerabilityDecision:
    """AnswerabilityDecision instantiation and defaults."""

    def test_defaults(self) -> None:
        ad = AnswerabilityDecision(answerable=True)
        assert ad.answerable is True
        assert ad.required_evidence == []
        assert ad.available_evidence == []
        assert ad.missing_evidence == []
        assert ad.confidence == 1.0
        assert ad.reason == ""
        assert ad.action == "answer"

    def test_clarify_action(self) -> None:
        ad = AnswerabilityDecision(
            answerable=False,
            required_evidence=["customer_profile"],
            available_evidence=[],
            missing_evidence=["customer_profile (no customer selected)"],
            confidence=0.0,
            reason="Customer query requires a customer profile but none is selected.",
            action="clarify",
        )
        assert ad.answerable is False
        assert ad.action == "clarify"
        assert "customer_profile" in ad.required_evidence
        assert ad.confidence == 0.0

    def test_refuse_action(self) -> None:
        ad = AnswerabilityDecision(
            answerable=False,
            required_evidence=["policy_chunks"],
            available_evidence=[],
            missing_evidence=["policy_chunks"],
            confidence=0.0,
            reason="No relevant context retrieved.",
            action="refuse_insufficient_context",
        )
        assert ad.answerable is False
        assert ad.action == "refuse_insufficient_context"

    def test_mutable_defaults_independent(self) -> None:
        a = AnswerabilityDecision(answerable=True)
        b = AnswerabilityDecision(answerable=True)
        a.required_evidence.append("x")
        assert "x" not in b.required_evidence

    def test_low_confidence_answer(self) -> None:
        ad = AnswerabilityDecision(
            answerable=True,
            confidence=0.3,
            reason="Sufficient evidence available.",
            action="answer",
        )
        assert ad.answerable is True
        assert ad.confidence == 0.3


class TestFaithfulnessStatus:
    """FaithfulnessStatus constants."""

    def test_status_constants(self) -> None:
        assert FaithfulnessStatus.PASSED == "passed"
        assert FaithfulnessStatus.FAILED_UNSUPPORTED == "failed_unsupported_claims"
        assert FaithfulnessStatus.FAILED_VERIFICATION_ERROR == "failed_verification_error"
        assert FaithfulnessStatus.FAILED_NO_CONTEXT == "failed_no_context"

    def test_faithfulness_result_status_default(self) -> None:
        fr = FaithfulnessResult(score=1.0)
        assert fr.status == "passed"

    def test_faithfulness_result_custom_status(self) -> None:
        fr = FaithfulnessResult(score=0.0, status=FaithfulnessStatus.FAILED_NO_CONTEXT)
        assert fr.status == "failed_no_context"


class TestTestQuery:
    def test_defaults(self) -> None:
        tq = TestQuery(
            query_id="TQ-001",
            query="What is X?",
            domain="product",
            difficulty="easy",
            expected_answer="X is Y.",
        )
        assert tq.expected_chunk_ids == []
        assert tq.customer_id is None


class TestEvalResult:
    def test_create(self) -> None:
        er = EvalResult(
            query_id="TQ-001",
            recall_at_5=0.8,
            mrr=0.5,
            context_precision=0.6,
            faithfulness=0.9,
            answer_relevance=0.85,
            has_hallucination=False,
            latency_ms=120.0,
        )
        assert er.recall_at_5 == 0.8
        assert er.has_hallucination is False


# ═══════════════════════════════════════════════════════════════════════════
# 2. ChunkMetadata domain validation
# ═══════════════════════════════════════════════════════════════════════════


class TestChunkMetadataDomainValidation:
    """Verify that ChunkMetadata accepts the expected domain values.

    The design specifies domain must be "product" or "policy".
    These tests document the valid domain values and ensure the
    dataclass stores them correctly.
    """

    VALID_DOMAINS = ("product", "policy")

    @pytest.mark.parametrize("domain", VALID_DOMAINS)
    def test_valid_domains_accepted(self, domain: str) -> None:
        meta = ChunkMetadata(domain=domain)
        assert meta.domain == domain

    def test_product_domain_allows_product_fields(self) -> None:
        meta = ChunkMetadata(
            domain="product",
            product_id="ALO-001",
            category="leggings",
            fabric_type="Airlift",
        )
        assert meta.product_id == "ALO-001"
        assert meta.policy_type is None

    def test_policy_domain_allows_policy_fields(self) -> None:
        meta = ChunkMetadata(
            domain="policy",
            policy_type="returns",
            effective_date="2024-06-01",
        )
        assert meta.policy_type == "returns"
        assert meta.product_id is None

    def test_domain_stored_as_given(self) -> None:
        """Domain value is stored exactly as provided (no normalization)."""
        meta = ChunkMetadata(domain="PRODUCT")
        assert meta.domain == "PRODUCT"

    def test_domain_is_required(self) -> None:
        """ChunkMetadata cannot be created without a domain argument."""
        with pytest.raises(TypeError):
            ChunkMetadata()  # type: ignore[call-arg]


# ═══════════════════════════════════════════════════════════════════════════
# 3. IntentClassification — ambiguity and multi-domain logic
# ═══════════════════════════════════════════════════════════════════════════


class TestIntentClassificationAmbiguity:
    """Verify the ambiguity flag semantics.

    Per the design, is_ambiguous should be True when the max domain
    confidence is below 0.3 (AMBIGUITY_THRESHOLD).
    """

    def test_not_ambiguous_when_high_confidence(self) -> None:
        ic = _make_intent(product=0.9, policy=0.05, customer=0.05, is_ambiguous=False)
        assert ic.is_ambiguous is False

    def test_ambiguous_when_all_scores_below_threshold(self) -> None:
        ic = _make_intent(
            product=0.2,
            policy=0.15,
            customer=0.1,
            is_ambiguous=True,
            primary_domain="product",
        )
        assert ic.is_ambiguous is True
        # All scores below 0.3
        assert all(v < 0.3 for v in ic.domains.values())

    def test_not_ambiguous_when_one_score_at_threshold(self) -> None:
        ic = _make_intent(
            product=0.3,
            policy=0.1,
            customer=0.1,
            is_ambiguous=False,
            primary_domain="product",
        )
        assert ic.is_ambiguous is False

    def test_ambiguous_query_primary_domain_still_set(self) -> None:
        """Even ambiguous queries should report the highest-scoring domain."""
        ic = _make_intent(
            product=0.25,
            policy=0.2,
            customer=0.1,
            is_ambiguous=True,
            primary_domain="product",
        )
        assert ic.primary_domain == "product"


class TestIntentClassificationMultiDomain:
    """Verify the multi-domain flag semantics.

    Per the design, is_multi_domain should be True when 2+ domains
    have confidence > 0.3 (MULTI_DOMAIN_THRESHOLD).
    """

    def test_single_domain(self) -> None:
        ic = _make_intent(
            product=0.8, policy=0.1, customer=0.1, is_multi_domain=False
        )
        assert ic.is_multi_domain is False

    def test_two_domains_above_threshold(self) -> None:
        ic = _make_intent(
            product=0.5,
            policy=0.4,
            customer=0.1,
            is_multi_domain=True,
            primary_domain="product",
        )
        assert ic.is_multi_domain is True
        above = [d for d, s in ic.domains.items() if s > 0.3]
        assert len(above) == 2

    def test_all_three_domains_above_threshold(self) -> None:
        ic = _make_intent(
            product=0.4,
            policy=0.35,
            customer=0.35,
            is_multi_domain=True,
            primary_domain="product",
        )
        assert ic.is_multi_domain is True
        above = [d for d, s in ic.domains.items() if s > 0.3]
        assert len(above) == 3

    def test_multi_domain_and_ambiguous_are_independent(self) -> None:
        """A query can be multi-domain without being ambiguous and vice versa."""
        # Multi-domain but not ambiguous (two domains > 0.3)
        ic1 = _make_intent(
            product=0.5, policy=0.4, customer=0.1,
            is_ambiguous=False, is_multi_domain=True,
        )
        assert ic1.is_multi_domain is True
        assert ic1.is_ambiguous is False

        # Ambiguous but not multi-domain (all < 0.3)
        ic2 = _make_intent(
            product=0.2, policy=0.15, customer=0.1,
            is_ambiguous=True, is_multi_domain=False,
        )
        assert ic2.is_ambiguous is True
        assert ic2.is_multi_domain is False

    def test_primary_domain_is_highest_scoring(self) -> None:
        ic = _make_intent(
            product=0.3,
            policy=0.6,
            customer=0.1,
            is_multi_domain=True,
            primary_domain="policy",
        )
        assert ic.primary_domain == "policy"
        assert ic.domains[ic.primary_domain] == max(ic.domains.values())


class TestIntentClassificationDomainScores:
    """Additional tests for domain score structure."""

    def test_domains_dict_has_three_keys(self) -> None:
        ic = _make_intent()
        assert set(ic.domains.keys()) == {"product", "policy", "customer"}

    def test_scores_are_floats_between_0_and_1(self) -> None:
        ic = _make_intent(product=0.7, policy=0.2, customer=0.1)
        for score in ic.domains.values():
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0

    def test_confidence_scores_stored_exactly(self) -> None:
        ic = _make_intent(product=0.85, policy=0.10, customer=0.05)
        assert ic.domains["product"] == 0.85
        assert ic.domains["policy"] == 0.10
        assert ic.domains["customer"] == 0.05
