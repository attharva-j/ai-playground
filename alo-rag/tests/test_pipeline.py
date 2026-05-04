"""Unit tests for the pipeline orchestrator.

Verifies the full RAG pipeline flow with mocked components:
- Full pipeline flow with mocked components
- HyDE activation for policy queries
- Query decomposition for multi-domain queries
- Scope guard integration for out-of-scope queries
- Error handling when a pipeline stage fails
- Trace log completeness

Requirements: 5.1, 6.1, 7.1, 8.1, 11.1, 20.1, 20.3
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from src.generation.customer_context import CustomerContextInjector
from src.generation.guardrails import FaithfulnessGuardrail
from src.generation.llm_client import LLMClient
from src.generation.prompt_builder import GenerationPrompt, PromptBuilder
from src.ingestion.embedders import EmbeddingService
from src.models import (
    Chunk,
    ChunkMetadata,
    Claim,
    CustomerProfile,
    FaithfulnessResult,
    IntentClassification,
    Order,
    OrderItem,
    PipelineResult,
    RetrievedChunk,
    ScopeDecision,
    SubQuery,
    TraceLog,
)
from src.pipeline import Pipeline, _ERROR_RESPONSE
from src.query.decomposer import QueryDecomposer
from src.query.hyde import HyDEModule
from src.query.intent_router import IntentRouter
from src.query.scope_guard import ScopeGuard
from src.retrieval.hybrid_search import HybridSearch


# ---------------------------------------------------------------------------
# Test fixtures and helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    chunk_id: str = "CHUNK-001",
    text: str = "Sample chunk text.",
    domain: str = "product",
    product_id: str | None = "ALO-LEG-001",
    policy_type: str | None = None,
) -> Chunk:
    """Create a Chunk with sensible defaults."""
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        metadata=ChunkMetadata(
            domain=domain,
            product_id=product_id,
            policy_type=policy_type,
        ),
        source_document="test_source.json",
    )


def _make_retrieved_chunk(
    chunk_id: str = "CHUNK-001",
    text: str = "Sample chunk text.",
    score: float = 0.85,
    source: str = "reranked",
    domain: str = "product",
) -> RetrievedChunk:
    """Create a RetrievedChunk with sensible defaults."""
    return RetrievedChunk(
        chunk=_make_chunk(chunk_id=chunk_id, text=text, domain=domain),
        score=score,
        source=source,
    )


def _make_classification(
    domains: dict[str, float] | None = None,
    primary_domain: str = "product",
    is_ambiguous: bool = False,
    is_multi_domain: bool = False,
) -> IntentClassification:
    """Create an IntentClassification with sensible defaults."""
    if domains is None:
        domains = {"product": 0.8, "policy": 0.1, "customer": 0.1}
    return IntentClassification(
        domains=domains,
        is_ambiguous=is_ambiguous,
        is_multi_domain=is_multi_domain,
        primary_domain=primary_domain,
    )


def _make_faithfulness_result(
    score: float = 1.0,
    regeneration_triggered: bool = False,
    regenerated_answer: str | None = None,
) -> FaithfulnessResult:
    """Create a FaithfulnessResult with sensible defaults."""
    return FaithfulnessResult(
        score=score,
        claims=[Claim(text="Test claim", supported=True, supporting_chunk_id="CHUNK-001")],
        unsupported_claims=[],
        regeneration_triggered=regeneration_triggered,
        regenerated_answer=regenerated_answer,
    )


def _make_generation_prompt(
    query: str = "test query",
    rendered: str = "Rendered prompt text",
) -> GenerationPrompt:
    """Create a GenerationPrompt with sensible defaults."""
    return GenerationPrompt(
        system_message="You are an ALO Yoga assistant.",
        context_chunks=[],
        customer_context=None,
        query=query,
        rendered=rendered,
    )


def _make_customer_profile() -> CustomerProfile:
    """Create a sample CustomerProfile."""
    return CustomerProfile(
        customer_id="CUST-001",
        name="Sarah Chen",
        email="sarah.chen@example.com",
        loyalty_tier="gold",
        orders=[
            Order(
                order_id="ORD-2024-001",
                date="2024-01-15",
                items=[
                    OrderItem(
                        product_id="ALO-LEG-001",
                        product_name="Airlift High-Waist Legging",
                        quantity=1,
                        price=118.00,
                        size="S",
                        was_discounted=False,
                        discount_pct=0,
                        final_sale=False,
                    )
                ],
                status="delivered",
                total=118.00,
            )
        ],
    )


def _build_pipeline(
    intent_router: MagicMock | None = None,
    hyde: MagicMock | None = None,
    decomposer: MagicMock | None = None,
    scope_guard: MagicMock | None = None,
    retrieval: MagicMock | None = None,
    prompt_builder: MagicMock | None = None,
    llm_client: MagicMock | None = None,
    guardrail: MagicMock | None = None,
    customer_injector: MagicMock | None = None,
    embedding_service: MagicMock | None = None,
) -> Pipeline:
    """Build a Pipeline with mocked components, using sensible defaults.

    Any component not explicitly provided gets a mock with default
    return values that produce a successful pipeline run.
    """
    if intent_router is None:
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification()

    if hyde is None:
        hyde = MagicMock(spec=HyDEModule)
        hyde.generate_hypothetical.return_value = "Hypothetical answer."
        hyde.embed_hypothetical.return_value = [0.5, 0.6, 0.7]
        hyde.process.return_value = [0.5, 0.6, 0.7]

    if decomposer is None:
        decomposer = MagicMock(spec=QueryDecomposer)
        decomposer.decompose.return_value = [
            SubQuery(text="test query", target_domain="product", original_query="test query"),
        ]

    if scope_guard is None:
        scope_guard = MagicMock(spec=ScopeGuard)
        scope_guard.evaluate.return_value = ScopeDecision(
            is_in_scope=True,
            reason="In scope.",
        )

    if retrieval is None:
        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [
            _make_retrieved_chunk("CHUNK-001", "Airlift leggings are made of nylon.", 0.92),
            _make_retrieved_chunk("CHUNK-002", "Available in sizes XXS to XL.", 0.85),
        ]

    if prompt_builder is None:
        prompt_builder = MagicMock(spec=PromptBuilder)
        prompt_builder.build.return_value = _make_generation_prompt()

    if llm_client is None:
        llm_client = MagicMock(spec=LLMClient)
        llm_client.generate.return_value = "The Airlift leggings are made of nylon and spandex."

    if guardrail is None:
        guardrail = MagicMock(spec=FaithfulnessGuardrail)
        guardrail.verify.return_value = _make_faithfulness_result()

    if customer_injector is None:
        customer_injector = MagicMock(spec=CustomerContextInjector)
        customer_injector.get_customer.return_value = None

    if embedding_service is None:
        embedding_service = MagicMock(spec=EmbeddingService)
        embedding_service.embed_single.return_value = [0.1, 0.2, 0.3]

    return Pipeline(
        intent_router=intent_router,
        hyde=hyde,
        decomposer=decomposer,
        scope_guard=scope_guard,
        retrieval=retrieval,
        prompt_builder=prompt_builder,
        llm_client=llm_client,
        guardrail=guardrail,
        customer_injector=customer_injector,
        embedding_service=embedding_service,
    )


# ===========================================================================
# 1. Full pipeline flow with mocked components
# ===========================================================================


class TestPipelineFullFlow:
    """Test the complete pipeline flow with all components mocked."""

    def test_basic_product_query_returns_answer(self) -> None:
        """A simple product query flows through all stages and returns an answer."""
        pipeline = _build_pipeline()

        result = pipeline.run("What are the Airlift leggings made of?")

        assert isinstance(result, PipelineResult)
        assert result.answer == "The Airlift leggings are made of nylon and spandex."
        assert result.faithfulness_score == 1.0
        assert len(result.chunks) == 2

    def test_pipeline_calls_all_stages_in_order(self) -> None:
        """All pipeline stages are called for a standard product query."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification()

        decomposer = MagicMock(spec=QueryDecomposer)
        decomposer.decompose.return_value = [
            SubQuery(text="test", target_domain="product", original_query="test"),
        ]

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk()]

        prompt_builder = MagicMock(spec=PromptBuilder)
        prompt_builder.build.return_value = _make_generation_prompt()

        llm_client = MagicMock(spec=LLMClient)
        llm_client.generate.return_value = "Answer text."

        guardrail = MagicMock(spec=FaithfulnessGuardrail)
        guardrail.verify.return_value = _make_faithfulness_result()

        embedding_service = MagicMock(spec=EmbeddingService)
        embedding_service.embed_single.return_value = [0.1, 0.2, 0.3]

        pipeline = _build_pipeline(
            intent_router=intent_router,
            decomposer=decomposer,
            retrieval=retrieval,
            prompt_builder=prompt_builder,
            llm_client=llm_client,
            guardrail=guardrail,
            embedding_service=embedding_service,
        )

        pipeline.run("test")

        intent_router.classify.assert_called_once_with("test")
        # Decomposition may be skipped for single-domain queries (fast path)
        retrieval.search.assert_called_once()
        prompt_builder.build.assert_called_once()
        llm_client.generate.assert_called_once()
        guardrail.verify.assert_called_once()

    def test_pipeline_with_customer_id_injects_context(self) -> None:
        """When customer_id is provided, customer context is fetched and passed to prompt builder."""
        customer_injector = MagicMock(spec=CustomerContextInjector)
        profile = _make_customer_profile()
        customer_injector.get_customer.return_value = profile

        prompt_builder = MagicMock(spec=PromptBuilder)
        prompt_builder.build.return_value = _make_generation_prompt()

        pipeline = _build_pipeline(
            customer_injector=customer_injector,
            prompt_builder=prompt_builder,
        )

        pipeline.run("What did I order?", customer_id="CUST-001")

        customer_injector.get_customer.assert_called_once_with("CUST-001")
        # Verify customer profile was passed to prompt builder
        call_kwargs = prompt_builder.build.call_args
        assert call_kwargs.kwargs.get("customer_context") == profile or (
            len(call_kwargs.args) >= 3 and call_kwargs.args[2] == profile
        )

    def test_pipeline_without_customer_id_skips_injection(self) -> None:
        """When no customer_id is provided, customer context injection is skipped."""
        customer_injector = MagicMock(spec=CustomerContextInjector)

        pipeline = _build_pipeline(customer_injector=customer_injector)

        pipeline.run("What are the leggings made of?")

        customer_injector.get_customer.assert_not_called()

    def test_pipeline_uses_regenerated_answer_when_triggered(self) -> None:
        """When faithfulness guardrail triggers regeneration, the regenerated answer is used."""
        guardrail = MagicMock(spec=FaithfulnessGuardrail)
        guardrail.verify.return_value = FaithfulnessResult(
            score=0.8,
            claims=[
                Claim(text="Claim 1", supported=True, supporting_chunk_id="C1"),
                Claim(text="Claim 2", supported=False),
            ],
            unsupported_claims=[Claim(text="Claim 2", supported=False)],
            regeneration_triggered=True,
            regenerated_answer="Regenerated answer with only supported claims.",
        )

        pipeline = _build_pipeline(guardrail=guardrail)

        result = pipeline.run("test query")

        assert result.answer == "Regenerated answer with only supported claims."
        assert result.faithfulness_score == 0.8

    def test_scope_guard_not_called_for_non_ambiguous_query(self) -> None:
        """Scope guard is only called when the query is ambiguous."""
        scope_guard = MagicMock(spec=ScopeGuard)

        pipeline = _build_pipeline(scope_guard=scope_guard)

        pipeline.run("What are the Airlift leggings made of?")

        scope_guard.evaluate.assert_not_called()


# ===========================================================================
# 2. HyDE activation for policy queries
# ===========================================================================


class TestPipelineHyDEActivation:
    """Test HyDE activation logic within the pipeline."""

    def test_hyde_activates_for_policy_query_above_threshold(self) -> None:
        """R6.1: HyDE is activated when policy confidence > 0.5."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.1, "policy": 0.7, "customer": 0.2},
            primary_domain="policy",
        )

        hyde = MagicMock(spec=HyDEModule)
        hyde.generate_hypothetical.return_value = "Returns accepted within 30 days."
        hyde.embed_hypothetical.return_value = [0.4, 0.5, 0.6]

        pipeline = _build_pipeline(intent_router=intent_router, hyde=hyde)

        result = pipeline.run("What is the return window for sale items?")

        hyde.generate_hypothetical.assert_called_once()
        hyde.embed_hypothetical.assert_called_once()
        assert result.trace.hyde_activated is True
        assert result.trace.hyde_hypothetical == "Returns accepted within 30 days."

    def test_hyde_not_activated_for_product_query(self) -> None:
        """R6.1: HyDE is NOT activated for product queries."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.9, "policy": 0.05, "customer": 0.05},
            primary_domain="product",
        )

        hyde = MagicMock(spec=HyDEModule)

        pipeline = _build_pipeline(intent_router=intent_router, hyde=hyde)

        result = pipeline.run("What are the Airlift leggings made of?")

        hyde.generate_hypothetical.assert_not_called()
        hyde.embed_hypothetical.assert_not_called()
        assert result.trace.hyde_activated is False
        assert result.trace.hyde_hypothetical is None

    def test_hyde_not_activated_for_policy_below_threshold(self) -> None:
        """R6.1: HyDE is NOT activated when policy confidence <= 0.5."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.3, "policy": 0.5, "customer": 0.2},
            primary_domain="policy",
        )

        hyde = MagicMock(spec=HyDEModule)

        pipeline = _build_pipeline(intent_router=intent_router, hyde=hyde)

        result = pipeline.run("Something about policies?")

        hyde.generate_hypothetical.assert_not_called()
        assert result.trace.hyde_activated is False

    def test_hyde_embedding_used_for_retrieval(self) -> None:
        """R6.2: When HyDE is activated, its embedding is used for dense retrieval."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.1, "policy": 0.8, "customer": 0.1},
            primary_domain="policy",
        )

        hyde = MagicMock(spec=HyDEModule)
        hyde_embedding = [0.9, 0.8, 0.7]
        hyde.generate_hypothetical.return_value = "Hypothetical policy text."
        hyde.embed_hypothetical.return_value = hyde_embedding

        # Decomposer must return a policy sub-query so the pipeline uses the HyDE embedding
        decomposer = MagicMock(spec=QueryDecomposer)
        decomposer.decompose.return_value = [
            SubQuery(text="What is the return policy?", target_domain="policy", original_query="What is the return policy?"),
        ]

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk(domain="policy")]

        embedding_service = MagicMock(spec=EmbeddingService)

        pipeline = _build_pipeline(
            intent_router=intent_router,
            hyde=hyde,
            decomposer=decomposer,
            retrieval=retrieval,
            embedding_service=embedding_service,
        )

        pipeline.run("What is the return policy?")

        # The retrieval should have been called with the HyDE embedding
        call_kwargs = retrieval.search.call_args
        assert call_kwargs.kwargs["query_embedding"] == hyde_embedding
        # Standard embedding should NOT have been called for the policy sub-query
        embedding_service.embed_single.assert_not_called()

    def test_hyde_failure_falls_back_to_standard_embedding(self) -> None:
        """R20.3: If HyDE fails, pipeline falls back to standard query embedding."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.1, "policy": 0.8, "customer": 0.1},
            primary_domain="policy",
        )

        hyde = MagicMock(spec=HyDEModule)
        hyde.generate_hypothetical.side_effect = RuntimeError("HyDE LLM failed")

        embedding_service = MagicMock(spec=EmbeddingService)
        embedding_service.embed_single.return_value = [0.1, 0.2, 0.3]

        pipeline = _build_pipeline(
            intent_router=intent_router,
            hyde=hyde,
            embedding_service=embedding_service,
        )

        result = pipeline.run("What is the return policy?")

        # Pipeline should still produce an answer (not crash)
        assert isinstance(result, PipelineResult)
        assert result.trace.hyde_activated is False
        # Standard embedding should have been used as fallback
        embedding_service.embed_single.assert_called()


# ===========================================================================
# 3. Query decomposition for multi-domain queries
# ===========================================================================


class TestPipelineQueryDecomposition:
    """Test query decomposition for multi-domain queries."""

    def test_multi_domain_query_triggers_decomposition(self) -> None:
        """R7.1: Multi-domain queries are decomposed into sub-queries."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.5, "policy": 0.4, "customer": 0.1},
            primary_domain="product",
            is_multi_domain=True,
        )

        sub_queries = [
            SubQuery(text="Tell me about the Airlift leggings.", target_domain="product", original_query="original"),
            SubQuery(text="What is the return policy?", target_domain="policy", original_query="original"),
        ]
        decomposer = MagicMock(spec=QueryDecomposer)
        decomposer.decompose.return_value = sub_queries

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk()]

        pipeline = _build_pipeline(
            intent_router=intent_router,
            decomposer=decomposer,
            retrieval=retrieval,
        )

        result = pipeline.run("What's the return policy for the Airlift leggings?")

        decomposer.decompose.assert_called_once()
        # Retrieval should be called once per sub-query
        assert retrieval.search.call_count == 2
        # Trace should record the decomposed queries
        assert result.trace.decomposed_queries is not None
        assert len(result.trace.decomposed_queries) == 2

    def test_single_domain_query_not_decomposed_in_trace(self) -> None:
        """Single-domain queries produce no decomposed_queries in the trace."""
        decomposer = MagicMock(spec=QueryDecomposer)
        decomposer.decompose.return_value = [
            SubQuery(text="test", target_domain="product", original_query="test"),
        ]

        pipeline = _build_pipeline(decomposer=decomposer)

        result = pipeline.run("What are the leggings made of?")

        # Single sub-query → decomposed_queries should be None in trace
        assert result.trace.decomposed_queries is None

    def test_decomposition_failure_falls_back_to_original_query(self) -> None:
        """R20.3: If decomposition fails, pipeline falls back to original query."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.5, "policy": 0.4, "customer": 0.1},
            primary_domain="product",
            is_multi_domain=True,
        )

        decomposer = MagicMock(spec=QueryDecomposer)
        decomposer.decompose.side_effect = RuntimeError("Decomposition failed")

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk()]

        pipeline = _build_pipeline(
            intent_router=intent_router,
            decomposer=decomposer,
            retrieval=retrieval,
        )

        result = pipeline.run("test query")

        # Pipeline should still produce an answer
        assert isinstance(result, PipelineResult)
        # Retrieval should still be called (with fallback sub-query)
        retrieval.search.assert_called()

    def test_multi_domain_retrieval_deduplicates_chunks(self) -> None:
        """When multiple sub-queries return the same chunk, it appears only once."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.5, "policy": 0.4, "customer": 0.1},
            primary_domain="product",
            is_multi_domain=True,
        )

        decomposer = MagicMock(spec=QueryDecomposer)
        decomposer.decompose.return_value = [
            SubQuery(text="sub1", target_domain="product", original_query="orig"),
            SubQuery(text="sub2", target_domain="policy", original_query="orig"),
        ]

        # Both sub-queries return the same chunk
        shared_chunk = _make_retrieved_chunk("SHARED-001", "Shared text.", 0.9)
        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [shared_chunk]

        pipeline = _build_pipeline(
            intent_router=intent_router,
            decomposer=decomposer,
            retrieval=retrieval,
        )

        result = pipeline.run("test")

        # The shared chunk should appear only once
        chunk_ids = [rc.chunk.chunk_id for rc in result.chunks]
        assert chunk_ids.count("SHARED-001") == 1


# ===========================================================================
# 4. Scope guard integration for out-of-scope queries
# ===========================================================================


class TestPipelineScopeGuard:
    """Test scope guard integration within the pipeline."""

    def test_out_of_scope_query_returns_refusal(self) -> None:
        """R11.2: Out-of-scope queries return a polite refusal, skipping retrieval."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.1, "policy": 0.1, "customer": 0.1},
            primary_domain="product",
            is_ambiguous=True,
        )

        scope_guard = MagicMock(spec=ScopeGuard)
        scope_guard.evaluate.return_value = ScopeDecision(
            is_in_scope=False,
            reason="Query is about cooking, not ALO Yoga.",
            suggested_response="I can only help with ALO Yoga topics.",
        )

        retrieval = MagicMock(spec=HybridSearch)
        llm_client = MagicMock(spec=LLMClient)

        pipeline = _build_pipeline(
            intent_router=intent_router,
            scope_guard=scope_guard,
            retrieval=retrieval,
            llm_client=llm_client,
        )

        result = pipeline.run("How do I make pasta?")

        scope_guard.evaluate.assert_called_once()
        assert result.answer == "I can only help with ALO Yoga topics."
        # Retrieval and generation should NOT be called for out-of-scope
        retrieval.search.assert_not_called()
        llm_client.generate.assert_not_called()
        assert result.chunks == []

    def test_ambiguous_in_scope_appends_uncertainty_note(self) -> None:
        """R11.3: Ambiguous in-scope queries get an uncertainty note appended."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.2, "policy": 0.15, "customer": 0.1},
            primary_domain="product",
            is_ambiguous=True,
        )

        uncertainty_text = "The query is ambiguous — the specific product is unclear."
        scope_guard = MagicMock(spec=ScopeGuard)
        scope_guard.evaluate.return_value = ScopeDecision(
            is_in_scope=True,
            reason="Could relate to ALO Yoga products.",
            uncertainty_note=uncertainty_text,
        )

        llm_client = MagicMock(spec=LLMClient)
        llm_client.generate.return_value = "Here is my best answer."

        pipeline = _build_pipeline(
            intent_router=intent_router,
            scope_guard=scope_guard,
            llm_client=llm_client,
        )

        result = pipeline.run("What material is this?")

        # The uncertainty note should be appended to the answer
        assert uncertainty_text in result.answer
        assert "Here is my best answer." in result.answer
        # Trace should record the scope decision
        assert result.trace.scope_decision is not None
        assert result.trace.scope_decision.uncertainty_note == uncertainty_text

    def test_ambiguous_in_scope_continues_pipeline(self) -> None:
        """R11.3: Ambiguous in-scope queries still go through retrieval and generation."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.2, "policy": 0.15, "customer": 0.1},
            primary_domain="product",
            is_ambiguous=True,
        )

        scope_guard = MagicMock(spec=ScopeGuard)
        scope_guard.evaluate.return_value = ScopeDecision(
            is_in_scope=True,
            reason="Possibly about ALO Yoga.",
            uncertainty_note="Ambiguous query.",
        )

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk()]

        llm_client = MagicMock(spec=LLMClient)
        llm_client.generate.return_value = "Generated answer."

        guardrail = MagicMock(spec=FaithfulnessGuardrail)
        guardrail.verify.return_value = _make_faithfulness_result()

        pipeline = _build_pipeline(
            intent_router=intent_router,
            scope_guard=scope_guard,
            retrieval=retrieval,
            llm_client=llm_client,
            guardrail=guardrail,
        )

        result = pipeline.run("What material is this?")

        retrieval.search.assert_called()
        llm_client.generate.assert_called()
        guardrail.verify.assert_called()

    def test_scope_guard_failure_defaults_to_in_scope(self) -> None:
        """R20.3: If scope guard fails, pipeline defaults to in-scope and continues."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.1, "policy": 0.1, "customer": 0.1},
            primary_domain="product",
            is_ambiguous=True,
        )

        scope_guard = MagicMock(spec=ScopeGuard)
        scope_guard.evaluate.side_effect = RuntimeError("Scope guard LLM failed")

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk()]

        llm_client = MagicMock(spec=LLMClient)
        llm_client.generate.return_value = "Answer despite scope guard failure."

        pipeline = _build_pipeline(
            intent_router=intent_router,
            scope_guard=scope_guard,
            retrieval=retrieval,
            llm_client=llm_client,
        )

        result = pipeline.run("ambiguous query")

        # Pipeline should still produce an answer
        assert isinstance(result, PipelineResult)
        retrieval.search.assert_called()
        llm_client.generate.assert_called()
        # Should have a fallback uncertainty note
        assert "best attempt" in result.answer.lower() or result.trace.scope_decision is not None


# ===========================================================================
# 5. Error handling when a pipeline stage fails
# ===========================================================================


class TestPipelineErrorHandling:
    """Test graceful error handling when pipeline stages fail."""

    def test_intent_classification_failure_returns_error_response(self) -> None:
        """R20.3: Intent classification failure returns a safe error response."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.side_effect = RuntimeError("API timeout")

        pipeline = _build_pipeline(intent_router=intent_router)

        result = pipeline.run("test query")

        assert result.answer == _ERROR_RESPONSE
        assert result.faithfulness_score is None
        assert result.chunks == []

    def test_retrieval_failure_continues_with_empty_chunks(self) -> None:
        """R20.3: Retrieval failure continues pipeline with empty chunks."""
        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.side_effect = RuntimeError("ChromaDB unavailable")

        llm_client = MagicMock(spec=LLMClient)
        llm_client.generate.return_value = "I don't have enough context to answer."

        pipeline = _build_pipeline(retrieval=retrieval, llm_client=llm_client)

        result = pipeline.run("test query")

        # Pipeline should still generate an answer (with empty context)
        assert isinstance(result, PipelineResult)
        llm_client.generate.assert_called()

    def test_prompt_building_failure_returns_error_response(self) -> None:
        """R20.3: Prompt building failure returns a safe error response."""
        prompt_builder = MagicMock(spec=PromptBuilder)
        prompt_builder.build.side_effect = RuntimeError("Template error")

        pipeline = _build_pipeline(prompt_builder=prompt_builder)

        result = pipeline.run("test query")

        assert result.answer == _ERROR_RESPONSE

    def test_llm_generation_failure_returns_error_response(self) -> None:
        """R20.3: LLM generation failure returns a safe error response."""
        llm_client = MagicMock(spec=LLMClient)
        llm_client.generate.side_effect = RuntimeError("OpenAI API error")

        pipeline = _build_pipeline(llm_client=llm_client)

        result = pipeline.run("test query")

        assert result.answer == _ERROR_RESPONSE

    def test_faithfulness_guardrail_failure_returns_original_answer(self) -> None:
        """R20.3: Guardrail failure returns the original answer (not error)."""
        llm_client = MagicMock(spec=LLMClient)
        llm_client.generate.return_value = "Original answer from LLM."

        guardrail = MagicMock(spec=FaithfulnessGuardrail)
        guardrail.verify.side_effect = RuntimeError("Verification failed")

        pipeline = _build_pipeline(llm_client=llm_client, guardrail=guardrail)

        result = pipeline.run("test query")

        # Original answer should be returned, not the error response
        assert result.answer == "Original answer from LLM."
        assert result.faithfulness_score is None

    def test_customer_context_failure_continues_without_profile(self) -> None:
        """R20.3: Customer context failure continues without customer data."""
        customer_injector = MagicMock(spec=CustomerContextInjector)
        customer_injector.get_customer.side_effect = RuntimeError("Data file missing")

        prompt_builder = MagicMock(spec=PromptBuilder)
        prompt_builder.build.return_value = _make_generation_prompt()

        pipeline = _build_pipeline(
            customer_injector=customer_injector,
            prompt_builder=prompt_builder,
        )

        result = pipeline.run("What did I order?", customer_id="CUST-001")

        # Pipeline should still produce an answer
        assert isinstance(result, PipelineResult)
        # Prompt builder should be called with None customer context
        call_kwargs = prompt_builder.build.call_args
        customer_arg = call_kwargs.kwargs.get("customer_context")
        assert customer_arg is None

    def test_error_result_has_valid_trace(self) -> None:
        """R20.3: Even error results include a valid trace log."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.side_effect = RuntimeError("API timeout")

        pipeline = _build_pipeline(intent_router=intent_router)

        result = pipeline.run("test query")

        assert result.trace is not None
        assert result.trace.query == "test query"
        assert result.trace.latency_ms >= 0
        assert isinstance(result.trace.intent_classification, IntentClassification)


# ===========================================================================
# 6. Trace log completeness
# ===========================================================================


class TestPipelineTraceLog:
    """Test that the trace log captures all pipeline decisions and timing."""

    def test_trace_contains_query(self) -> None:
        """R20.1: Trace log records the original query."""
        pipeline = _build_pipeline()

        result = pipeline.run("What are the Airlift leggings made of?")

        assert result.trace.query == "What are the Airlift leggings made of?"

    def test_trace_contains_timestamp(self) -> None:
        """R20.1: Trace log records a timestamp."""
        pipeline = _build_pipeline()

        result = pipeline.run("test")

        assert result.trace.timestamp is not None
        assert len(result.trace.timestamp) > 0

    def test_trace_contains_intent_classification(self) -> None:
        """R20.1: Trace log records intent classification result."""
        intent_router = MagicMock(spec=IntentRouter)
        classification = _make_classification(
            domains={"product": 0.9, "policy": 0.05, "customer": 0.05},
            primary_domain="product",
        )
        intent_router.classify.return_value = classification

        pipeline = _build_pipeline(intent_router=intent_router)

        result = pipeline.run("test")

        assert result.trace.intent_classification == classification
        assert result.trace.intent_classification.primary_domain == "product"

    def test_trace_contains_hyde_status(self) -> None:
        """R20.1: Trace log records whether HyDE was activated."""
        pipeline = _build_pipeline()

        result = pipeline.run("test")

        assert isinstance(result.trace.hyde_activated, bool)

    def test_trace_contains_retrieval_results(self) -> None:
        """R20.1: Trace log records retrieval results."""
        retrieval = MagicMock(spec=HybridSearch)
        chunks = [
            _make_retrieved_chunk("C1", "Text 1", 0.9),
            _make_retrieved_chunk("C2", "Text 2", 0.8),
        ]
        retrieval.search.return_value = chunks

        pipeline = _build_pipeline(retrieval=retrieval)

        result = pipeline.run("test")

        assert len(result.trace.retrieval_results) == 2

    def test_trace_contains_reranking_scores(self) -> None:
        """R20.1: Trace log records reranking scores."""
        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [
            _make_retrieved_chunk("C1", "Text 1", 0.92),
            _make_retrieved_chunk("C2", "Text 2", 0.85),
        ]

        pipeline = _build_pipeline(retrieval=retrieval)

        result = pipeline.run("test")

        assert result.trace.reranking_scores == [0.92, 0.85]

    def test_trace_contains_faithfulness_result(self) -> None:
        """R20.1: Trace log records faithfulness result."""
        guardrail = MagicMock(spec=FaithfulnessGuardrail)
        faith_result = _make_faithfulness_result(score=0.95)
        guardrail.verify.return_value = faith_result

        pipeline = _build_pipeline(guardrail=guardrail)

        result = pipeline.run("test")

        assert result.trace.faithfulness_result is not None
        assert result.trace.faithfulness_result.score == 0.95

    def test_trace_contains_total_latency(self) -> None:
        """R20.1: Trace log records end-to-end latency."""
        pipeline = _build_pipeline()

        result = pipeline.run("test")

        assert result.trace.latency_ms > 0

    def test_trace_contains_stage_latencies(self) -> None:
        """R20.1: Trace log records per-stage latencies."""
        pipeline = _build_pipeline()

        result = pipeline.run("test")

        latencies = result.trace.stage_latencies
        assert "intent_classification" in latencies
        # decomposition may be absent for single-domain queries (fast path)
        assert "retrieval" in latencies
        assert "prompt_building" in latencies
        assert "generation" in latencies
        assert "faithfulness_guardrail" in latencies
        # All latencies should be non-negative
        assert all(v >= 0 for v in latencies.values())

    def test_trace_records_scope_decision_when_ambiguous(self) -> None:
        """R20.1: Trace log records scope decision for ambiguous queries."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.1, "policy": 0.1, "customer": 0.1},
            primary_domain="product",
            is_ambiguous=True,
        )

        scope_decision = ScopeDecision(
            is_in_scope=True,
            reason="Possibly about ALO Yoga.",
            uncertainty_note="Ambiguous query.",
        )
        scope_guard = MagicMock(spec=ScopeGuard)
        scope_guard.evaluate.return_value = scope_decision

        pipeline = _build_pipeline(
            intent_router=intent_router,
            scope_guard=scope_guard,
        )

        result = pipeline.run("vague question")

        assert result.trace.scope_decision == scope_decision
        assert "scope_guard" in result.trace.stage_latencies

    def test_trace_records_no_scope_decision_for_clear_query(self) -> None:
        """R20.1: Trace log has no scope decision for non-ambiguous queries."""
        pipeline = _build_pipeline()

        result = pipeline.run("What are the Airlift leggings made of?")

        assert result.trace.scope_decision is None

    def test_trace_records_hyde_hypothetical_when_activated(self) -> None:
        """R6.3: Trace log records the hypothetical document when HyDE is activated."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.1, "policy": 0.8, "customer": 0.1},
            primary_domain="policy",
        )

        hyde = MagicMock(spec=HyDEModule)
        hyde.generate_hypothetical.return_value = "Returns are accepted within 30 days."
        hyde.embed_hypothetical.return_value = [0.5, 0.6, 0.7]

        pipeline = _build_pipeline(intent_router=intent_router, hyde=hyde)

        result = pipeline.run("What is the return window?")

        assert result.trace.hyde_hypothetical == "Returns are accepted within 30 days."
        assert "hyde" in result.trace.stage_latencies

    def test_trace_records_decomposed_queries_for_multi_domain(self) -> None:
        """R20.1: Trace log records decomposed sub-queries for multi-domain queries."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.5, "policy": 0.4, "customer": 0.1},
            primary_domain="product",
            is_multi_domain=True,
        )

        sub_queries = [
            SubQuery(text="About the product", target_domain="product", original_query="orig"),
            SubQuery(text="About the policy", target_domain="policy", original_query="orig"),
        ]
        decomposer = MagicMock(spec=QueryDecomposer)
        decomposer.decompose.return_value = sub_queries

        pipeline = _build_pipeline(
            intent_router=intent_router,
            decomposer=decomposer,
        )

        result = pipeline.run("multi-domain query")

        assert result.trace.decomposed_queries is not None
        assert len(result.trace.decomposed_queries) == 2
        assert result.trace.decomposed_queries[0].target_domain == "product"
        assert result.trace.decomposed_queries[1].target_domain == "policy"


# ===========================================================================
# 7. Metadata filtering in retrieval
# ===========================================================================


class TestPipelineMetadataFiltering:
    """Test that the pipeline applies correct metadata filters during retrieval."""

    def test_product_query_applies_domain_filter(self) -> None:
        """R8.4: Product queries apply domain='product' metadata filter."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.9, "policy": 0.05, "customer": 0.05},
            primary_domain="product",
        )

        decomposer = MagicMock(spec=QueryDecomposer)
        decomposer.decompose.return_value = [
            SubQuery(text="test", target_domain="product", original_query="test"),
        ]

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk()]

        pipeline = _build_pipeline(
            intent_router=intent_router,
            decomposer=decomposer,
            retrieval=retrieval,
        )

        pipeline.run("What are the leggings made of?")

        call_kwargs = retrieval.search.call_args.kwargs
        assert call_kwargs["metadata_filter"] == {"domain": "product"}

    def test_policy_query_applies_domain_filter(self) -> None:
        """R8.4: Policy queries apply domain='policy' metadata filter."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.05, "policy": 0.9, "customer": 0.05},
            primary_domain="policy",
        )

        decomposer = MagicMock(spec=QueryDecomposer)
        decomposer.decompose.return_value = [
            SubQuery(text="test", target_domain="policy", original_query="test"),
        ]

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk(domain="policy")]

        pipeline = _build_pipeline(
            intent_router=intent_router,
            decomposer=decomposer,
            retrieval=retrieval,
        )

        pipeline.run("What is the return policy?")

        call_kwargs = retrieval.search.call_args.kwargs
        assert call_kwargs["metadata_filter"] == {"domain": "policy"}

    def test_customer_query_has_no_metadata_filter(self) -> None:
        """R8.4: Customer queries don't apply metadata filter (structured lookup)."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.05, "policy": 0.05, "customer": 0.9},
            primary_domain="customer",
        )

        decomposer = MagicMock(spec=QueryDecomposer)
        decomposer.decompose.return_value = [
            SubQuery(text="test", target_domain="customer", original_query="test"),
        ]

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk()]

        pipeline = _build_pipeline(
            intent_router=intent_router,
            decomposer=decomposer,
            retrieval=retrieval,
        )

        pipeline.run("What did I order?")

        call_kwargs = retrieval.search.call_args.kwargs
        assert call_kwargs["metadata_filter"] is None


# ===========================================================================
# 7. Answerability gate tests
# ===========================================================================


class TestPipelineAnswerabilityGate:
    """Test the answerability gate in run_without_generation."""

    def test_customer_query_without_customer_id_returns_clarify(self) -> None:
        """Customer-domain query without customer_id triggers clarify refusal."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.1, "policy": 0.1, "customer": 0.8},
            primary_domain="customer",
        )

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk()]

        pipeline = _build_pipeline(
            intent_router=intent_router,
            retrieval=retrieval,
        )

        result = pipeline.run_without_generation("What did I order last month?")

        assert result.is_refused is True
        assert "customer" in result.refusal_message.lower() or "select" in result.refusal_message.lower()

    def test_customer_query_with_valid_customer_id_proceeds(self) -> None:
        """Customer-domain query with valid customer_id passes answerability."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.1, "policy": 0.1, "customer": 0.8},
            primary_domain="customer",
        )

        customer_injector = MagicMock(spec=CustomerContextInjector)
        customer_injector.get_customer.return_value = _make_customer_profile()

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk()]

        prompt_builder = MagicMock(spec=PromptBuilder)
        prompt_builder.build.return_value = _make_generation_prompt()

        pipeline = _build_pipeline(
            intent_router=intent_router,
            customer_injector=customer_injector,
            retrieval=retrieval,
            prompt_builder=prompt_builder,
        )

        result = pipeline.run_without_generation("What did I order?", customer_id="CUST-001")

        assert result.is_refused is False

    def test_customer_query_with_unknown_customer_id_refuses(self) -> None:
        """Customer-domain query with unknown customer_id triggers refuse."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.1, "policy": 0.1, "customer": 0.8},
            primary_domain="customer",
        )

        customer_injector = MagicMock(spec=CustomerContextInjector)
        customer_injector.get_customer.return_value = None

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk()]

        pipeline = _build_pipeline(
            intent_router=intent_router,
            customer_injector=customer_injector,
            retrieval=retrieval,
        )

        result = pipeline.run_without_generation("What did I order?", customer_id="UNKNOWN-999")

        assert result.is_refused is True
        assert "not found" in result.refusal_message.lower() or "enough information" in result.refusal_message.lower()

    def test_product_query_without_chunks_refuses(self) -> None:
        """Product query with no retrieved chunks triggers refuse."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.8, "policy": 0.1, "customer": 0.1},
            primary_domain="product",
        )

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = []

        pipeline = _build_pipeline(
            intent_router=intent_router,
            retrieval=retrieval,
        )

        result = pipeline.run_without_generation("Tell me about the XYZ product")

        assert result.is_refused is True
        assert "enough information" in result.refusal_message.lower() or "No relevant" in result.refusal_message

    def test_product_query_with_chunks_proceeds(self) -> None:
        """Product query with retrieved chunks passes answerability."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.8, "policy": 0.1, "customer": 0.1},
            primary_domain="product",
        )

        retrieval = MagicMock(spec=HybridSearch)
        retrieval.search.return_value = [_make_retrieved_chunk()]

        prompt_builder = MagicMock(spec=PromptBuilder)
        prompt_builder.build.return_value = _make_generation_prompt()

        pipeline = _build_pipeline(
            intent_router=intent_router,
            retrieval=retrieval,
            prompt_builder=prompt_builder,
        )

        result = pipeline.run_without_generation("What are the Airlift leggings made of?")

        assert result.is_refused is False


class TestCheckAnswerabilityMethod:
    """Direct tests for the _check_answerability method."""

    def test_answerable_with_all_evidence(self) -> None:
        """Returns answerable=True when all required evidence is available."""
        pipeline = _build_pipeline()
        classification = _make_classification(
            domains={"product": 0.8, "policy": 0.1, "customer": 0.1},
        )
        chunks = [_make_retrieved_chunk(score=0.9)]

        result = pipeline._check_answerability(
            query="test",
            classification=classification,
            customer_id=None,
            customer_profile=None,
            chunks=chunks,
        )

        assert result.answerable is True
        assert result.action == "answer"
        assert result.confidence == 1.0

    def test_low_confidence_for_low_score_chunks(self) -> None:
        """Returns low confidence when top chunk score is below threshold."""
        pipeline = _build_pipeline()
        classification = _make_classification(
            domains={"product": 0.8, "policy": 0.1, "customer": 0.1},
        )
        chunks = [_make_retrieved_chunk(score=-1.5)]

        result = pipeline._check_answerability(
            query="test",
            classification=classification,
            customer_id=None,
            customer_profile=None,
            chunks=chunks,
        )

        assert result.answerable is True
        assert result.confidence == 0.3

    def test_medium_confidence_for_negative_score(self) -> None:
        """Returns medium confidence when top chunk score is between -1.0 and 0."""
        pipeline = _build_pipeline()
        classification = _make_classification(
            domains={"product": 0.8, "policy": 0.1, "customer": 0.1},
        )
        chunks = [_make_retrieved_chunk(score=-0.5)]

        result = pipeline._check_answerability(
            query="test",
            classification=classification,
            customer_id=None,
            customer_profile=None,
            chunks=chunks,
        )

        assert result.answerable is True
        assert result.confidence == 0.6

    def test_clarify_for_customer_query_no_id(self) -> None:
        """Returns clarify when customer query has no customer_id."""
        pipeline = _build_pipeline()
        classification = _make_classification(
            domains={"product": 0.1, "policy": 0.1, "customer": 0.8},
        )
        chunks = [_make_retrieved_chunk()]

        result = pipeline._check_answerability(
            query="What did I order?",
            classification=classification,
            customer_id=None,
            customer_profile=None,
            chunks=chunks,
        )

        assert result.answerable is False
        assert result.action == "clarify"

    def test_refuse_for_customer_id_not_found(self) -> None:
        """Returns refuse when customer_id is provided but profile not found."""
        pipeline = _build_pipeline()
        classification = _make_classification(
            domains={"product": 0.1, "policy": 0.1, "customer": 0.8},
        )
        chunks = [_make_retrieved_chunk()]

        result = pipeline._check_answerability(
            query="What did I order?",
            classification=classification,
            customer_id="CUST-999",
            customer_profile=None,
            chunks=chunks,
        )

        assert result.answerable is False
        assert result.action == "refuse_insufficient_context"

    def test_refuse_for_no_chunks_with_requirements(self) -> None:
        """Returns refuse when no chunks retrieved but evidence is required."""
        pipeline = _build_pipeline()
        classification = _make_classification(
            domains={"product": 0.8, "policy": 0.1, "customer": 0.1},
        )

        result = pipeline._check_answerability(
            query="test",
            classification=classification,
            customer_id=None,
            customer_profile=None,
            chunks=[],
        )

        assert result.answerable is False
        assert result.action == "refuse_insufficient_context"

    def test_run_customer_query_without_customer_id_short_circuits() -> None:
        """Full pipeline.run() should short-circuit customer queries without customer_id."""
        intent_router = MagicMock(spec=IntentRouter)
        intent_router.classify.return_value = _make_classification(
            domains={"product": 0.05, "policy": 0.10, "customer": 0.85},
            primary_domain="customer",
            is_ambiguous=False,
            is_multi_domain=False,
        )

        retrieval = MagicMock(spec=HybridSearch)

        pipeline = _build_pipeline(
            intent_router=intent_router,
            retrieval=retrieval,
        )

        result = pipeline.run("What is the status of my order?")

        assert result.answerability_decision is not None
        assert result.answerability_decision.action == "clarify"
        assert "customer" in result.answer.lower()
        retrieval.search.assert_not_called()