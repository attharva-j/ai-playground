"""Core data models and types for the ALO RAG System.

All domain entities used across ingestion, query intelligence, retrieval,
generation, evaluation, and pipeline orchestration are defined here as
Python dataclasses with full type annotations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Ingestion models
# ---------------------------------------------------------------------------


@dataclass
class RawDocument:
    """A raw document loaded from a data source before chunking."""

    content: str
    source: str
    domain: str  # "product" | "policy" | "customer"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkMetadata:
    """Metadata attached to a document chunk for filtering and tracing."""

    domain: str  # "product" | "policy"
    product_id: str | None = None
    category: str | None = None
    fabric_type: str | None = None  # e.g. "Airlift", "Airbrush", "Alosoft"
    policy_type: str | None = None  # "returns" | "shipping" | "promo" | "loyalty"
    effective_date: str | None = None


@dataclass
class Chunk:
    """A segment of a source document produced by the ingestion pipeline."""

    chunk_id: str
    text: str
    metadata: ChunkMetadata
    source_document: str


# ---------------------------------------------------------------------------
# Retrieval models
# ---------------------------------------------------------------------------


@dataclass
class RetrievedChunk:
    """A chunk returned by the retrieval engine with a relevance score."""

    chunk: Chunk
    score: float
    source: str  # "dense" | "sparse" | "fused" | "reranked"


# ---------------------------------------------------------------------------
# Customer models
# ---------------------------------------------------------------------------


@dataclass
class OrderItem:
    """A single item within a customer order."""

    product_id: str
    product_name: str
    quantity: int
    price: float
    size: str
    was_discounted: bool
    discount_pct: int
    final_sale: bool


@dataclass
class Order:
    """A customer order containing one or more items."""

    order_id: str
    date: str
    items: list[OrderItem]
    status: str
    total: float


@dataclass
class CustomerProfile:
    """A customer profile with order history for structured lookup."""

    customer_id: str
    name: str
    email: str
    orders: list[Order] = field(default_factory=list)
    loyalty_tier: str = ""


# ---------------------------------------------------------------------------
# Query intelligence models
# ---------------------------------------------------------------------------


@dataclass
class IntentClassification:
    """Result of LLM-based intent routing with domain confidence scores."""

    domains: dict[str, float]  # e.g. {"product": 0.8, "policy": 0.1, "customer": 0.1}
    is_ambiguous: bool  # True if max confidence < 0.3
    is_multi_domain: bool  # True if 2+ domains > 0.3
    primary_domain: str  # Domain with highest confidence


@dataclass
class SubQuery:
    """A domain-specific sub-query produced by the query decomposer."""

    text: str
    target_domain: str
    original_query: str


@dataclass
class ScopeDecision:
    """Result of scope guard evaluation for ambiguous queries."""

    is_in_scope: bool
    reason: str
    suggested_response: str | None = None  # Polite refusal if out-of-scope
    uncertainty_note: str | None = None  # Appended to answer when in-scope but ambiguous


@dataclass
class AnswerabilityDecision:
    """Pre-generation gate that determines whether the system has sufficient
    evidence to produce a reliable answer."""

    answerable: bool
    required_evidence: list[str] = field(default_factory=list)
    available_evidence: list[str] = field(default_factory=list)
    missing_evidence: list[str] = field(default_factory=list)
    confidence: float = 1.0
    reason: str = ""
    action: str = "answer"  # "answer" | "clarify" | "refuse_insufficient_context"


# ---------------------------------------------------------------------------
# Faithfulness / guardrail models
# ---------------------------------------------------------------------------


@dataclass
class Claim:
    """A single factual claim extracted from a generated answer."""

    text: str
    supported: bool
    supporting_chunk_id: str | None = None


class FaithfulnessStatus:
    """Status constants for faithfulness verification."""
    PASSED = "passed"
    FAILED_UNSUPPORTED = "failed_unsupported_claims"
    FAILED_VERIFICATION_ERROR = "failed_verification_error"
    FAILED_NO_CONTEXT = "failed_no_context"


@dataclass
class EvidenceClaim:
    """Maps a generated answer claim to its supporting evidence source."""
    claim: str
    evidence_type: str  # "product" | "policy" | "customer" | "none"
    source_id: str | None = None
    supported: bool = False
    risk_level: str = "low"  # "low" | "medium" | "high"


@dataclass
class FaithfulnessResult:
    """Result of the faithfulness guardrail verification."""

    score: float  # 0.0 to 1.0
    claims: list[Claim] = field(default_factory=list)
    unsupported_claims: list[Claim] = field(default_factory=list)
    regeneration_triggered: bool = False
    regenerated_answer: str | None = None
    status: str = "passed"  # FaithfulnessStatus value


# ---------------------------------------------------------------------------
# Pipeline / tracing models
# ---------------------------------------------------------------------------


@dataclass
class TraceLog:
    """Structured trace log capturing every pipeline decision and timing."""

    query: str
    timestamp: str
    intent_classification: IntentClassification
    hyde_activated: bool
    hyde_hypothetical: str | None = None
    decomposed_queries: list[SubQuery] | None = None
    scope_decision: ScopeDecision | None = None
    answerability_decision: AnswerabilityDecision | None = None
    retrieval_results: list[RetrievedChunk] = field(default_factory=list)
    reranking_scores: list[float] = field(default_factory=list)
    faithfulness_result: FaithfulnessResult | None = None
    latency_ms: float = 0.0
    stage_latencies: dict[str, float] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Final result returned by the pipeline orchestrator."""

    answer: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
    trace: TraceLog | None = None
    faithfulness_score: float | None = None
    answerability_decision: AnswerabilityDecision | None = None
    evidence_claims: list[EvidenceClaim] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Evaluation models
# ---------------------------------------------------------------------------


@dataclass
class TestQuery:
    """A test query for the evaluation framework."""

    query_id: str
    query: str
    domain: str
    difficulty: str  # "easy" | "medium" | "hard"
    expected_answer: str
    expected_chunk_ids: list[str] = field(default_factory=list)
    customer_id: str | None = None


@dataclass
class EvalResult:
    """Evaluation result for a single test query."""

    query_id: str
    recall_at_5: float
    mrr: float
    context_precision: float
    faithfulness: float
    answer_relevance: float
    has_hallucination: bool
    latency_ms: float
