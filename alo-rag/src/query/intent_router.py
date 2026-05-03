"""LLM-based query intent router for the ALO RAG System.

Classifies incoming user queries into one or more knowledge domains
(product, policy, customer) with confidence scores using GPT-4o-mini.
The classification drives downstream routing decisions: HyDE activation,
query decomposition, and scope guard evaluation.

Requirements: 5.1, 5.2, 5.3, 5.4
"""

from __future__ import annotations

import json
import logging

from src.generation.llm_client import LLMClient
from src.models import IntentClassification

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Routing threshold constants
# ---------------------------------------------------------------------------

AMBIGUITY_THRESHOLD: float = 0.3
"""Max domain score below this → query is ambiguous (R5.3)."""

MULTI_DOMAIN_THRESHOLD: float = 0.3
"""Score above this in 2+ domains → multi-domain query (R5.4)."""

HYDE_THRESHOLD: float = 0.5
"""Policy score above this → activate HyDE for improved retrieval (R6.1)."""

# ---------------------------------------------------------------------------
# Valid domains
# ---------------------------------------------------------------------------

_VALID_DOMAINS: list[str] = ["product", "policy", "customer"]

# ---------------------------------------------------------------------------
# System prompt for intent classification
# ---------------------------------------------------------------------------

_CLASSIFICATION_SYSTEM_PROMPT: str = (
    "You are a query intent classifier for an ALO Yoga customer support system. "
    "Classify the user query into one or more knowledge domains with confidence "
    "scores between 0.0 and 1.0. The three domains are:\n\n"
    "- product: Questions about product specifications, materials, sizing, "
    "care instructions, fabric types, colours, pricing, or product comparisons.\n"
    "- policy: Questions about return policies, shipping SLAs, promotional "
    "eligibility rules, loyalty tier logic, or operational procedures.\n"
    "- customer: Questions about a specific customer's order history, loyalty "
    "status, past purchases, or account details.\n\n"
    "Respond with ONLY a JSON object containing confidence scores for each "
    "domain. The scores should sum to approximately 1.0. Example:\n"
    '{"product": 0.8, "policy": 0.1, "customer": 0.1}\n\n'
    "Do not include any text outside the JSON object."
)

# ---------------------------------------------------------------------------
# Default classification (safe fallback)
# ---------------------------------------------------------------------------

_DEFAULT_DOMAINS: dict[str, float] = {
    "product": 0.0,
    "policy": 0.0,
    "customer": 0.0,
}


class IntentRouter:
    """LLM-based query intent classifier using GPT-4o-mini.

    Uses :meth:`LLMClient.classify` (Haiku) to produce domain confidence
    scores for each incoming query.  The classification result drives
    downstream pipeline decisions:

    * **Ambiguous** (max score < 0.3) → Scope Guard evaluation (R5.3)
    * **Multi-domain** (2+ domains > 0.3) → Query Decomposer (R5.4)
    * **Policy with confidence > 0.5** → HyDE activation (R6.1)

    Parameters
    ----------
    llm_client:
        An :class:`LLMClient` instance used for the Haiku classification call.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def classify(self, query: str) -> IntentClassification:
        """Classify a user query into knowledge domains with confidence scores.

        Calls GPT-4o-mini via :meth:`LLMClient.classify` and parses the
        JSON response into an :class:`IntentClassification`.  If the LLM
        response cannot be parsed as valid JSON, a safe default
        classification is returned with all scores at 0.0 (flagged as
        ambiguous).

        Parameters
        ----------
        query:
            The user's natural language query.

        Returns
        -------
        IntentClassification
            Domain confidence scores and routing flags.
        """
        logger.debug("IntentRouter.classify() called — query=%r", query)

        # Try rule-based fast path first
        fast_result = self._try_fast_path(query)
        if fast_result is not None:
            logger.info("IntentRouter — fast path match: primary=%s", fast_result.primary_domain)
            return fast_result

        # Fall back to LLM classification
        try:
            raw_response = self._llm_client.classify(
                prompt=query,
                system=_CLASSIFICATION_SYSTEM_PROMPT,
            )
            domains = self._parse_response(raw_response)
        except Exception:
            logger.exception("IntentRouter.classify() — LLM call or parsing failed")
            domains = dict(_DEFAULT_DOMAINS)

        return self._build_classification(domains)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_fast_path(self, query: str) -> IntentClassification | None:
        """Attempt rule-based classification before calling the LLM.

        Returns an IntentClassification if the query matches a known
        pattern, or None if the LLM should be consulted.
        """
        q = query.lower()

        # Customer signals
        customer_signals = ["my order", "my return", "my purchase", "my points",
                           "my account", "my loyalty", "what did i buy",
                           "order status", "my shipment", "my delivery"]
        has_customer = any(sig in q for sig in customer_signals)

        # Policy signals
        policy_signals = ["exchange policy", "shipping policy",
                         "return window", "refund", "final sale", "loyalty tier",
                         "loyalty points", "promo", "discount", "coupon",
                         "free shipping", "prepaid label", "international return"]
        has_policy = any(sig in q for sig in policy_signals)

        # Product signals — very specific product-only patterns
        product_signals = ["alosoft", "softsculpt",
                          "moto legging", "goddess legging",
                          "care instruction", "how to wash"]
        has_product = any(sig in q for sig in product_signals)

        # Count how many domains matched — only fast-path if exactly one
        matches = sum([has_customer, has_policy, has_product])
        if matches != 1:
            return None  # Ambiguous or no match — use LLM

        if has_customer:
            return self._build_classification(
                {"product": 0.05, "policy": 0.15, "customer": 0.8}
            )

        if has_policy:
            return self._build_classification(
                {"product": 0.05, "policy": 0.85, "customer": 0.1}
            )

        if has_product:
            return self._build_classification(
                {"product": 0.85, "policy": 0.05, "customer": 0.1}
            )

        return None  # No fast path match — use LLM

    def _parse_response(self, raw: str) -> dict[str, float]:
        """Parse the LLM JSON response into a domain-score mapping.

        Handles common edge cases:
        * Strips markdown code fences if present.
        * Clamps scores to [0.0, 1.0].
        * Fills missing domains with 0.0.
        * Ignores unexpected domain keys.

        Returns a dict with exactly the three valid domain keys.
        """
        cleaned = raw.strip()

        # Strip markdown code fences that LLMs sometimes add
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            # Remove first and last fence lines
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        parsed = json.loads(cleaned)

        if not isinstance(parsed, dict):
            logger.warning(
                "IntentRouter._parse_response() — expected dict, got %s",
                type(parsed).__name__,
            )
            return dict(_DEFAULT_DOMAINS)

        domains: dict[str, float] = {}
        for domain in _VALID_DOMAINS:
            raw_score = parsed.get(domain, 0.0)
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                score = 0.0
            domains[domain] = max(0.0, min(1.0, score))

        return domains

    @staticmethod
    def _build_classification(domains: dict[str, float]) -> IntentClassification:
        """Construct an IntentClassification from domain scores."""
        max_score = max(domains.values()) if domains else 0.0
        primary_domain = max(domains, key=domains.get) if domains else "product"  # type: ignore[arg-type]

        is_ambiguous = max_score < AMBIGUITY_THRESHOLD
        high_scoring = [d for d, s in domains.items() if s > MULTI_DOMAIN_THRESHOLD]
        is_multi_domain = len(high_scoring) >= 2

        classification = IntentClassification(
            domains=domains,
            is_ambiguous=is_ambiguous,
            is_multi_domain=is_multi_domain,
            primary_domain=primary_domain,
        )

        logger.debug(
            "IntentRouter — classification=%s",
            classification,
        )
        return classification
