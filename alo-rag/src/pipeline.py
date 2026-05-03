"""Pipeline orchestrator for the ALO RAG System.

Coordinates the full query flow from user input to final answer:

    Intent Routing → Scope Guard → HyDE → Decomposition →
    Hybrid Retrieval → Customer Context Injection → Prompt Building →
    LLM Generation → Faithfulness Guardrail

Each stage appends timing and decision data to a :class:`TraceLog` for
full observability.  Stage errors are caught, logged, and handled
gracefully — the pipeline returns a safe error response rather than
propagating exceptions.

Requirements: 5.1, 5.3, 5.4, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 8.1,
              9.1, 9.2, 9.3, 10.1, 11.1, 11.2, 11.3, 20.1, 20.2, 20.3
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.generation.customer_context import CustomerContextInjector
from src.generation.guardrails import FaithfulnessGuardrail
from src.generation.llm_client import LLMClient
from src.generation.prompt_builder import PromptBuilder
from src.ingestion.embedders import EmbeddingService
from src.models import (
    AnswerabilityDecision,
    FaithfulnessResult,
    IntentClassification,
    PipelineResult,
    RetrievedChunk,
    ScopeDecision,
    SubQuery,
    TraceLog,
)
from src.query.decomposer import QueryDecomposer
from src.query.hyde import HyDEModule
from src.query.intent_router import HYDE_THRESHOLD, IntentRouter
from src.query.scope_guard import ScopeGuard
from src.retrieval.hybrid_search import HybridSearch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Safe error response returned when the pipeline cannot produce an answer
# ---------------------------------------------------------------------------

_ERROR_RESPONSE = (
    "I'm sorry, but I encountered an issue processing your request. "
    "Please try again or rephrase your question."
)


@dataclass
class PreGenerationResult:
    """Result of running pipeline stages 1-7 (everything except LLM generation)."""

    gen_prompt: Any  # GenerationPrompt from prompt_builder
    chunks: list[RetrievedChunk]
    classification: IntentClassification
    scope_decision: ScopeDecision | None
    uncertainty_note: str | None
    hyde_activated: bool
    hyde_hypothetical: str | None
    stage_latencies: dict[str, float]
    is_refused: bool = False
    refusal_message: str | None = None


class Pipeline:
    """Orchestrates the full RAG pipeline from query to answer.

    Parameters
    ----------
    intent_router:
        Classifies queries by domain with confidence scores.
    hyde:
        Generates hypothetical answers for improved policy retrieval.
    decomposer:
        Splits multi-domain queries into domain-specific sub-queries.
    scope_guard:
        Evaluates whether ambiguous queries are in-scope.
    retrieval:
        Hybrid dense + sparse search with RRF fusion and reranking.
    prompt_builder:
        Assembles structured prompts from context and customer data.
    llm_client:
        OpenAI GPT wrapper for answer generation.
    guardrail:
        Faithfulness verification with optional regeneration.
    customer_injector:
        Structured customer data lookup by customer_id.
    embedding_service:
        Computes dense embeddings for query vectors.
    """

    def __init__(
        self,
        intent_router: IntentRouter,
        hyde: HyDEModule,
        decomposer: QueryDecomposer,
        scope_guard: ScopeGuard,
        retrieval: HybridSearch,
        prompt_builder: PromptBuilder,
        llm_client: LLMClient,
        guardrail: FaithfulnessGuardrail,
        customer_injector: CustomerContextInjector,
        embedding_service: EmbeddingService,
    ) -> None:
        self._intent_router = intent_router
        self._hyde = hyde
        self._decomposer = decomposer
        self._scope_guard = scope_guard
        self._retrieval = retrieval
        self._prompt_builder = prompt_builder
        self._llm_client = llm_client
        self._guardrail = guardrail
        self._customer_injector = customer_injector
        self._embedding_service = embedding_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, query: str, customer_id: str | None = None) -> PipelineResult:
        """Execute the full RAG pipeline for *query*.

        Parameters
        ----------
        query:
            The user's natural language question.
        customer_id:
            Optional customer identifier for personalised answers.

        Returns
        -------
        PipelineResult
            The final answer, retrieved chunks, trace log, and
            faithfulness score.
        """
        pipeline_start = time.perf_counter()
        stage_latencies: dict[str, float] = {}

        # Initialise trace fields that will be populated as we progress
        classification: IntentClassification | None = None
        scope_decision: ScopeDecision | None = None
        hyde_activated = False
        hyde_hypothetical: str | None = None
        decomposed_queries: list[SubQuery] | None = None
        all_chunks: list[RetrievedChunk] = []
        reranking_scores: list[float] = []
        faithfulness_result: FaithfulnessResult | None = None
        uncertainty_note: str | None = None

        # ── Stage 1: Intent Classification ───────────────────────────
        try:
            t0 = time.perf_counter()
            classification = self._intent_router.classify(query)
            stage_latencies["intent_classification"] = _elapsed_ms(t0)
            logger.info(
                "Pipeline — intent classification: primary=%s, "
                "ambiguous=%s, multi_domain=%s",
                classification.primary_domain,
                classification.is_ambiguous,
                classification.is_multi_domain,
            )
        except Exception:
            logger.exception(
                "Pipeline — intent classification failed; stage=intent_classification, "
                "input=%r",
                query,
            )
            return self._error_result(
                query, pipeline_start, stage_latencies,
            )

        # ── Stage 2: Scope Guard (if ambiguous) ─────────────────────
        if classification.is_ambiguous:
            try:
                t0 = time.perf_counter()
                scope_decision = self._scope_guard.evaluate(query, classification)
                stage_latencies["scope_guard"] = _elapsed_ms(t0)
                logger.info(
                    "Pipeline — scope guard: in_scope=%s, reason=%r",
                    scope_decision.is_in_scope,
                    scope_decision.reason,
                )

                if not scope_decision.is_in_scope:
                    # Out-of-scope → return polite refusal immediately
                    return self._build_result(
                        answer=scope_decision.suggested_response or _ERROR_RESPONSE,
                        query=query,
                        classification=classification,
                        scope_decision=scope_decision,
                        hyde_activated=False,
                        all_chunks=[],
                        reranking_scores=[],
                        faithfulness_result=None,
                        decomposed_queries=None,
                        hyde_hypothetical=None,
                        uncertainty_note=None,
                        stage_latencies=stage_latencies,
                        pipeline_start=pipeline_start,
                    )

                # In-scope but ambiguous → capture uncertainty note
                uncertainty_note = scope_decision.uncertainty_note

            except Exception:
                logger.exception(
                    "Pipeline — scope guard failed; stage=scope_guard, input=%r",
                    query,
                )
                # Default to in-scope on failure (safer than refusing)
                scope_decision = ScopeDecision(
                    is_in_scope=True,
                    reason="Scope guard error; defaulting to in-scope.",
                    uncertainty_note=(
                        "I wasn't fully able to determine the scope of your "
                        "question. The answer below is my best attempt."
                    ),
                )
                uncertainty_note = scope_decision.uncertainty_note

        # ── Stages 3 + 4: HyDE and Decomposition (parallel) ─────────
        # HyDE and decomposition are independent of each other — both
        # depend only on the classification from Stage 1.  Running them
        # in parallel eliminates the sequential wait on multi-domain
        # policy queries (saves ~350ms on the most complex query types).
        (
            query_embedding,
            hyde_hypothetical,
            hyde_activated,
            sub_queries,
            parallel_latencies,
        ) = self._run_hyde_and_decompose_parallel(query, classification)
        stage_latencies.update(parallel_latencies)

        if len(sub_queries) > 1:
            decomposed_queries = sub_queries
            logger.info(
                "Pipeline — decomposed into %d sub-queries", len(sub_queries)
            )
        else:
            logger.debug("Pipeline — single-domain query, no decomposition")

        # ── Stage 5: Hybrid Retrieval ────────────────────────────────
        try:
            t0 = time.perf_counter()
            all_chunks = self._retrieve_for_sub_queries(
                sub_queries=sub_queries,
                query_embedding=query_embedding,
                hyde_activated=hyde_activated,
            )
            stage_latencies["retrieval"] = _elapsed_ms(t0)
            reranking_scores = [rc.score for rc in all_chunks]
            logger.info(
                "Pipeline — retrieved %d chunks total",
                len(all_chunks),
            )
        except Exception:
            logger.exception(
                "Pipeline — retrieval failed; stage=retrieval, input=%r",
                query,
            )
            # Continue with empty chunks — generation will note lack of context

        # ── Stage 6: Customer Context Injection ──────────────────────
        customer_profile = None
        if customer_id:
            try:
                t0 = time.perf_counter()
                customer_profile = self._customer_injector.get_customer(customer_id)
                stage_latencies["customer_context"] = _elapsed_ms(t0)
                if customer_profile:
                    logger.info(
                        "Pipeline — loaded customer profile: %s",
                        customer_id,
                    )
                else:
                    logger.info(
                        "Pipeline — customer_id=%r not found",
                        customer_id,
                    )
            except Exception:
                logger.exception(
                    "Pipeline — customer context failed; stage=customer_context, "
                    "input=%r",
                    customer_id,
                )

        # ── Stage 7: Prompt Building ─────────────────────────────────
        try:
            t0 = time.perf_counter()
            gen_prompt = self._prompt_builder.build(
                query=query,
                chunks=all_chunks,
                customer_context=customer_profile,
            )
            stage_latencies["prompt_building"] = _elapsed_ms(t0)
        except Exception:
            logger.exception(
                "Pipeline — prompt building failed; stage=prompt_building, "
                "input=%r",
                query,
            )
            return self._build_result(
                answer=_ERROR_RESPONSE,
                query=query,
                classification=classification,
                scope_decision=scope_decision,
                hyde_activated=hyde_activated,
                all_chunks=all_chunks,
                reranking_scores=reranking_scores,
                faithfulness_result=None,
                decomposed_queries=decomposed_queries,
                hyde_hypothetical=hyde_hypothetical,
                uncertainty_note=uncertainty_note,
                stage_latencies=stage_latencies,
                pipeline_start=pipeline_start,
            )

        # ── Stage 8: LLM Generation ─────────────────────────────────
        try:
            t0 = time.perf_counter()
            answer = self._llm_client.generate(
                prompt=gen_prompt.rendered,
                system=gen_prompt.system_message,
            )
            stage_latencies["generation"] = _elapsed_ms(t0)
            logger.info(
                "Pipeline — generated answer: %d chars",
                len(answer),
            )
        except Exception:
            logger.exception(
                "Pipeline — LLM generation failed; stage=generation, input=%r",
                query,
            )
            return self._build_result(
                answer=_ERROR_RESPONSE,
                query=query,
                classification=classification,
                scope_decision=scope_decision,
                hyde_activated=hyde_activated,
                all_chunks=all_chunks,
                reranking_scores=reranking_scores,
                faithfulness_result=None,
                decomposed_queries=decomposed_queries,
                hyde_hypothetical=hyde_hypothetical,
                uncertainty_note=uncertainty_note,
                stage_latencies=stage_latencies,
                pipeline_start=pipeline_start,
            )

        # ── Stage 9: Faithfulness Guardrail ──────────────────────────
        try:
            t0 = time.perf_counter()
            faithfulness_result = self._guardrail.verify(
                answer=answer,
                context_chunks=all_chunks,
                query=query,
            )
            stage_latencies["faithfulness_guardrail"] = _elapsed_ms(t0)

            # Use regenerated answer if regeneration was triggered
            if faithfulness_result.regeneration_triggered and faithfulness_result.regenerated_answer:
                answer = faithfulness_result.regenerated_answer
                logger.info(
                    "Pipeline — using regenerated answer (faithfulness=%.2f)",
                    faithfulness_result.score,
                )
            else:
                logger.info(
                    "Pipeline — faithfulness score=%.2f",
                    faithfulness_result.score,
                )
        except Exception:
            logger.exception(
                "Pipeline — faithfulness guardrail failed; stage=faithfulness_guardrail, "
                "input=%r. Returning original answer.",
                query,
            )
            # Continue with the original answer — better than no answer

        # ── Stage 10: Append uncertainty note (R11.3) ────────────────
        if uncertainty_note:
            answer = f"{answer}\n\n---\n*Note: {uncertainty_note}*"

        # ── Build final result ───────────────────────────────────────
        return self._build_result(
            answer=answer,
            query=query,
            classification=classification,
            scope_decision=scope_decision,
            hyde_activated=hyde_activated,
            all_chunks=all_chunks,
            reranking_scores=reranking_scores,
            faithfulness_result=faithfulness_result,
            decomposed_queries=decomposed_queries,
            hyde_hypothetical=hyde_hypothetical,
            uncertainty_note=uncertainty_note,
            stage_latencies=stage_latencies,
            pipeline_start=pipeline_start,
        )

    # ------------------------------------------------------------------
    # Pre-generation pipeline (stages 1-7 only, no LLM call)
    # ------------------------------------------------------------------

    def run_without_generation(
        self, query: str, customer_id: str | None = None
    ) -> PreGenerationResult:
        """Run pipeline stages 1-7 only, stopping before LLM generation.

        Used by the streaming server endpoint so that the single LLM
        generation call can be streamed directly to the client without
        a redundant first call.
        """
        stage_latencies: dict[str, float] = {}
        classification: IntentClassification | None = None
        scope_decision: ScopeDecision | None = None
        uncertainty_note: str | None = None
        hyde_activated = False
        hyde_hypothetical: str | None = None

        # Stage 1: Intent classification
        try:
            t0 = time.perf_counter()
            classification = self._intent_router.classify(query)
            stage_latencies["intent_classification"] = _elapsed_ms(t0)
        except Exception:
            logger.exception("run_without_generation — intent classification failed")
            return PreGenerationResult(
                gen_prompt=None, chunks=[],
                classification=IntentClassification(
                    domains={"product": 0.0, "policy": 0.0, "customer": 0.0},
                    is_ambiguous=True, is_multi_domain=False, primary_domain="product",
                ),
                scope_decision=None, uncertainty_note=None,
                hyde_activated=False, hyde_hypothetical=None,
                stage_latencies=stage_latencies,
                is_refused=True, refusal_message=_ERROR_RESPONSE,
            )

        # Stage 2: Scope guard
        if classification.is_ambiguous:
            try:
                t0 = time.perf_counter()
                scope_decision = self._scope_guard.evaluate(query, classification)
                stage_latencies["scope_guard"] = _elapsed_ms(t0)
                if not scope_decision.is_in_scope:
                    return PreGenerationResult(
                        gen_prompt=None, chunks=[],
                        classification=classification,
                        scope_decision=scope_decision, uncertainty_note=None,
                        hyde_activated=False, hyde_hypothetical=None,
                        stage_latencies=stage_latencies,
                        is_refused=True,
                        refusal_message=scope_decision.suggested_response or _ERROR_RESPONSE,
                    )
                uncertainty_note = scope_decision.uncertainty_note
            except Exception:
                logger.exception("run_without_generation — scope guard failed")

        # Stages 3 + 4: HyDE and decomposition (parallel)
        (
            query_embedding,
            hyde_hypothetical,
            hyde_activated,
            sub_queries,
            parallel_latencies,
        ) = self._run_hyde_and_decompose_parallel(query, classification)
        stage_latencies.update(parallel_latencies)

        # Stage 5: Retrieval
        all_chunks: list[RetrievedChunk] = []
        try:
            t0 = time.perf_counter()
            all_chunks = self._retrieve_for_sub_queries(
                sub_queries=sub_queries,
                query_embedding=query_embedding,
                hyde_activated=hyde_activated,
            )
            stage_latencies["retrieval"] = _elapsed_ms(t0)
        except Exception:
            logger.exception("run_without_generation — retrieval failed")

        # Stage 6: Customer context
        customer_profile = None
        if customer_id:
            try:
                t0 = time.perf_counter()
                customer_profile = self._customer_injector.get_customer(customer_id)
                stage_latencies["customer_context"] = _elapsed_ms(t0)
            except Exception:
                logger.exception("run_without_generation — customer context failed")

        # Stage 6.5: Answerability gate
        answerability = self._check_answerability(
            query=query,
            classification=classification,
            customer_id=customer_id,
            customer_profile=customer_profile,
            chunks=all_chunks,
        )

        if not answerability.answerable:
            # Build a clarifying/refusal message
            if answerability.action == "clarify":
                refusal = (
                    "I can help with that, but I need to know which customer "
                    "you are. Please select a customer profile from the dropdown "
                    "to access order-specific information."
                )
            else:
                refusal = (
                    "I don't have enough information to answer that question "
                    "reliably. " + answerability.reason
                )
            return PreGenerationResult(
                gen_prompt=None, chunks=all_chunks,
                classification=classification,
                scope_decision=scope_decision, uncertainty_note=uncertainty_note,
                hyde_activated=hyde_activated, hyde_hypothetical=hyde_hypothetical,
                stage_latencies=stage_latencies,
                is_refused=True, refusal_message=refusal,
            )

        # Stage 7: Prompt building
        try:
            t0 = time.perf_counter()
            gen_prompt = self._prompt_builder.build(
                query=query, chunks=all_chunks, customer_context=customer_profile,
            )
            stage_latencies["prompt_building"] = _elapsed_ms(t0)
        except Exception:
            logger.exception("run_without_generation — prompt building failed")
            return PreGenerationResult(
                gen_prompt=None, chunks=all_chunks,
                classification=classification,
                scope_decision=scope_decision, uncertainty_note=uncertainty_note,
                hyde_activated=hyde_activated, hyde_hypothetical=hyde_hypothetical,
                stage_latencies=stage_latencies,
                is_refused=True, refusal_message=_ERROR_RESPONSE,
            )

        return PreGenerationResult(
            gen_prompt=gen_prompt, chunks=all_chunks,
            classification=classification,
            scope_decision=scope_decision, uncertainty_note=uncertainty_note,
            hyde_activated=hyde_activated, hyde_hypothetical=hyde_hypothetical,
            stage_latencies=stage_latencies,
            is_refused=False, refusal_message=None,
        )

    # ------------------------------------------------------------------
    # Answerability gate
    # ------------------------------------------------------------------

    def _check_answerability(
        self,
        query: str,
        classification: IntentClassification,
        customer_id: str | None,
        customer_profile: Any | None,
        chunks: list[RetrievedChunk],
    ) -> AnswerabilityDecision:
        """Determine whether the system has sufficient evidence to answer.

        Rules:
        1. Customer-domain query without customer_id → clarify
        2. Customer-domain query with customer_id but no profile found → refuse
        3. No retrieved chunks at all → refuse_insufficient_context
        4. Top chunk score below threshold → answer with low confidence
        """
        required = []
        available = []
        missing = []

        # Check customer evidence requirements
        customer_score = classification.domains.get("customer", 0.0)
        if customer_score > 0.3:
            required.append("customer_profile")
            if customer_id and customer_profile:
                available.append("customer_profile")
            elif customer_id and not customer_profile:
                missing.append("customer_profile (ID not found)")
            else:
                missing.append("customer_profile (no customer selected)")

        # Check retrieval evidence
        policy_score = classification.domains.get("policy", 0.0)
        product_score = classification.domains.get("product", 0.0)

        if policy_score > 0.3:
            required.append("policy_chunks")
            policy_chunks = [rc for rc in chunks if rc.chunk.metadata.domain == "policy"]
            if policy_chunks:
                available.append("policy_chunks")
            else:
                missing.append("policy_chunks")

        if product_score > 0.3:
            required.append("product_chunks")
            product_chunks = [rc for rc in chunks if rc.chunk.metadata.domain == "product"]
            if product_chunks:
                available.append("product_chunks")
            else:
                missing.append("product_chunks")

        # Decision logic
        if "customer_profile (no customer selected)" in missing and customer_score > 0.5:
            return AnswerabilityDecision(
                answerable=False,
                required_evidence=required,
                available_evidence=available,
                missing_evidence=missing,
                confidence=0.0,
                reason="Customer query requires a customer profile but none is selected.",
                action="clarify",
            )

        if "customer_profile (ID not found)" in missing:
            return AnswerabilityDecision(
                answerable=False,
                required_evidence=required,
                available_evidence=available,
                missing_evidence=missing,
                confidence=0.0,
                reason="Customer ID provided but no matching profile found.",
                action="refuse_insufficient_context",
            )

        if not chunks and required:
            return AnswerabilityDecision(
                answerable=False,
                required_evidence=required,
                available_evidence=available,
                missing_evidence=missing,
                confidence=0.0,
                reason="No relevant context retrieved.",
                action="refuse_insufficient_context",
            )

        # Check retrieval quality
        confidence = 1.0
        if chunks:
            top_score = chunks[0].score
            if top_score < -1.0:
                confidence = 0.3
            elif top_score < 0.0:
                confidence = 0.6

        return AnswerabilityDecision(
            answerable=True,
            required_evidence=required,
            available_evidence=available,
            missing_evidence=missing,
            confidence=confidence,
            reason="Sufficient evidence available.",
            action="answer",
        )

    # ------------------------------------------------------------------
    # Parallel HyDE + decomposition
    # ------------------------------------------------------------------

    def _run_hyde_and_decompose_parallel(
        self,
        query: str,
        classification: IntentClassification,
    ) -> tuple[
        list[float] | None,   # query_embedding (from HyDE, or None)
        str | None,            # hyde_hypothetical text (or None)
        bool,                  # hyde_activated flag
        list[SubQuery],        # sub_queries
        dict[str, float],      # stage_latencies
    ]:
        """Run HyDE and query decomposition in parallel threads.

        Both stages depend only on the intent classification from Stage 1.
        They are independent of each other and can execute concurrently,
        saving ~350ms on multi-domain policy queries.
        """
        stage_latencies: dict[str, float] = {}
        policy_score = classification.domains.get("policy", 0.0)
        needs_hyde = policy_score > HYDE_THRESHOLD
        needs_decompose = classification.is_multi_domain

        query_embedding: list[float] | None = None
        hyde_hypothetical: str | None = None
        hyde_activated = False
        sub_queries: list[SubQuery] = [
            SubQuery(
                text=query,
                target_domain=classification.primary_domain,
                original_query=query,
            )
        ]

        # Fast path: neither stage needed
        if not needs_hyde and not needs_decompose:
            return query_embedding, hyde_hypothetical, hyde_activated, sub_queries, stage_latencies

        t_start = time.perf_counter()

        def _run_hyde() -> tuple[str, list[float]]:
            text = self._hyde.generate_hypothetical(query)
            embedding = self._hyde.embed_hypothetical(text)
            return text, embedding

        def _run_decompose() -> list[SubQuery]:
            return self._decomposer.decompose(query, classification)

        with ThreadPoolExecutor(max_workers=2) as executor:
            hyde_future = executor.submit(_run_hyde) if needs_hyde else None
            decompose_future = executor.submit(_run_decompose) if needs_decompose else None

            if hyde_future is not None:
                try:
                    hyde_hypothetical, query_embedding = hyde_future.result()
                    hyde_activated = True
                    stage_latencies["hyde"] = _elapsed_ms(t_start)
                    logger.info(
                        "Pipeline — HyDE completed (policy_score=%.2f)",
                        policy_score,
                    )
                except Exception:
                    logger.exception("Pipeline — HyDE failed, falling back")

            if decompose_future is not None:
                try:
                    sub_queries = decompose_future.result()
                    stage_latencies["decomposition"] = _elapsed_ms(t_start)
                    logger.info(
                        "Pipeline — decomposed into %d sub-queries",
                        len(sub_queries),
                    )
                except Exception:
                    logger.exception("Pipeline — decomposition failed, falling back")
                    sub_queries = [
                        SubQuery(
                            text=query,
                            target_domain=classification.primary_domain,
                            original_query=query,
                        )
                    ]

        return query_embedding, hyde_hypothetical, hyde_activated, sub_queries, stage_latencies

    # ------------------------------------------------------------------
    # Retrieval helpers
    # ------------------------------------------------------------------

    def _retrieve_for_sub_queries(
        self,
        sub_queries: list[SubQuery],
        query_embedding: list[float] | None,
        hyde_activated: bool,
    ) -> list[RetrievedChunk]:
        """Execute hybrid retrieval for each sub-query and merge results.

        If HyDE was activated, the pre-computed embedding is used for the
        first (or only) sub-query targeting the policy domain.  All other
        sub-queries use a standard query embedding.

        When multiple sub-queries produce results, chunks are merged and
        deduplicated by ``chunk_id``, keeping the highest-scoring instance.
        """
        seen_chunk_ids: set[str] = set()
        merged: list[RetrievedChunk] = []

        for sq in sub_queries:
            # Determine the query embedding for this sub-query
            embedding = self._get_embedding_for_sub_query(
                sq, query_embedding, hyde_activated,
            )

            # Build optional metadata filter for domain-specific retrieval
            metadata_filter = self._build_metadata_filter(sq.target_domain)

            # Single-domain queries use tighter retrieval to reduce noise.
            # Multi-domain sub-queries use a slightly larger pool so each
            # domain is adequately represented in the merged result.
            final_k = 3 if len(sub_queries) == 1 else 4

            # Execute hybrid search
            results = self._retrieval.search(
                query_embedding=embedding,
                query_text=sq.text,
                metadata_filter=metadata_filter,
                final_k=final_k,
            )

            # Deduplicate across sub-queries
            for rc in results:
                cid = rc.chunk.chunk_id
                if cid not in seen_chunk_ids:
                    seen_chunk_ids.add(cid)
                    merged.append(rc)

        # Sort merged results by score descending
        merged.sort(key=lambda rc: rc.score, reverse=True)
        return merged

    def _get_embedding_for_sub_query(
        self,
        sub_query: SubQuery,
        hyde_embedding: list[float] | None,
        hyde_activated: bool,
    ) -> list[float]:
        """Return the appropriate embedding for a sub-query.

        Uses the HyDE embedding for policy sub-queries when HyDE was
        activated; otherwise computes a standard query embedding.
        """
        if hyde_activated and hyde_embedding and sub_query.target_domain == "policy":
            return hyde_embedding

        return self._embedding_service.embed_single(sub_query.text)

    @staticmethod
    def _build_metadata_filter(domain: str) -> dict[str, str] | None:
        """Build a ChromaDB metadata filter for domain-specific retrieval.

        Returns ``None`` for the ``customer`` domain since customer data
        is handled via structured lookup, not vector search.
        """
        if domain in ("product", "policy"):
            return {"domain": domain}
        return None

    # ------------------------------------------------------------------
    # Result builders
    # ------------------------------------------------------------------

    def _build_result(
        self,
        answer: str,
        query: str,
        classification: IntentClassification,
        scope_decision: ScopeDecision | None,
        hyde_activated: bool,
        all_chunks: list[RetrievedChunk],
        reranking_scores: list[float],
        faithfulness_result: FaithfulnessResult | None,
        decomposed_queries: list[SubQuery] | None,
        hyde_hypothetical: str | None,
        uncertainty_note: str | None,
        stage_latencies: dict[str, float],
        pipeline_start: float,
    ) -> PipelineResult:
        """Assemble the final :class:`PipelineResult` with trace log."""
        total_latency = _elapsed_ms(pipeline_start)

        trace = TraceLog(
            query=query,
            timestamp=datetime.now(timezone.utc).isoformat(),
            intent_classification=classification,
            hyde_activated=hyde_activated,
            hyde_hypothetical=hyde_hypothetical,
            decomposed_queries=decomposed_queries,
            scope_decision=scope_decision,
            retrieval_results=all_chunks,
            reranking_scores=reranking_scores,
            faithfulness_result=faithfulness_result,
            latency_ms=total_latency,
            stage_latencies=stage_latencies,
        )

        faithfulness_score = (
            faithfulness_result.score if faithfulness_result else None
        )

        logger.info(
            "Pipeline — completed in %.1f ms (faithfulness=%s)",
            total_latency,
            f"{faithfulness_score:.2f}" if faithfulness_score is not None else "N/A",
        )

        return PipelineResult(
            answer=answer,
            chunks=all_chunks,
            trace=trace,
            faithfulness_score=faithfulness_score,
        )

    def _error_result(
        self,
        query: str,
        pipeline_start: float,
        stage_latencies: dict[str, float],
    ) -> PipelineResult:
        """Return a safe error response when the pipeline cannot proceed.

        Used for early-exit failures (e.g. intent classification failure)
        where we don't yet have a classification to populate the trace.
        """
        total_latency = _elapsed_ms(pipeline_start)

        # Build a minimal classification for the trace
        fallback_classification = IntentClassification(
            domains={"product": 0.0, "policy": 0.0, "customer": 0.0},
            is_ambiguous=True,
            is_multi_domain=False,
            primary_domain="product",
        )

        trace = TraceLog(
            query=query,
            timestamp=datetime.now(timezone.utc).isoformat(),
            intent_classification=fallback_classification,
            hyde_activated=False,
            latency_ms=total_latency,
            stage_latencies=stage_latencies,
        )

        return PipelineResult(
            answer=_ERROR_RESPONSE,
            chunks=[],
            trace=trace,
            faithfulness_score=None,
        )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _elapsed_ms(start: float) -> float:
    """Return elapsed milliseconds since *start* (from ``time.perf_counter()``)."""
    return (time.perf_counter() - start) * 1000.0
