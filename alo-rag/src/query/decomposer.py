"""Query decomposer for the ALO RAG System.

Splits multi-domain queries into domain-specific sub-queries so that
each part is answered using the optimal retrieval strategy for its
domain.  Uses GPT-4o-mini via :meth:`LLMClient.classify` for the
decomposition — it is a lightweight structured-output task.

Requirements: 7.1, 7.2
"""

from __future__ import annotations

import json
import logging

from src.generation.llm_client import LLMClient
from src.models import IntentClassification, SubQuery
from src.query.intent_router import MULTI_DOMAIN_THRESHOLD

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for query decomposition
# ---------------------------------------------------------------------------

_DECOMPOSITION_SYSTEM_PROMPT: str = (
    "You are a query decomposition engine for an ALO Yoga customer support system. "
    "Given a user query and a list of relevant knowledge domains, break the query "
    "into independent sub-queries — one per domain.\n\n"
    "The three possible domains are:\n"
    "- product: Questions about product specifications, materials, sizing, "
    "care instructions, fabric types, colours, pricing, or product comparisons.\n"
    "- policy: Questions about return policies, shipping SLAs, promotional "
    "eligibility rules, loyalty tier logic, or operational procedures.\n"
    "- customer: Questions about a specific customer's order history, loyalty "
    "status, past purchases, or account details.\n\n"
    "Rules:\n"
    "- Each sub-query must be a self-contained question targeting exactly one domain.\n"
    "- Preserve the user's original intent — do not add information that was not in "
    "the original query.\n"
    "- Each sub-query should be phrased as a natural question.\n\n"
    "Respond with ONLY a JSON array of objects. Each object must have:\n"
    '  - "text": the sub-query text\n'
    '  - "domain": one of "product", "policy", or "customer"\n\n'
    "Example:\n"
    '[{"text": "What is the return policy for sale items?", "domain": "policy"}, '
    '{"text": "What leggings did I buy last month?", "domain": "customer"}]\n\n'
    "Do not include any text outside the JSON array."
)


class QueryDecomposer:
    """Splits multi-domain queries into domain-specific sub-queries.

    When the :class:`IntentRouter` assigns confidence scores above
    :data:`MULTI_DOMAIN_THRESHOLD` (0.3) to two or more domains, this
    decomposer uses GPT-4o-mini to break the query into independent
    sub-queries — one per relevant domain.  Each sub-query is then
    routed to the retrieval strategy appropriate for its domain (R7.2).

    For single-domain queries (only one domain above the threshold),
    the decomposer returns a single :class:`SubQuery` targeting the
    primary domain without making an LLM call.

    Parameters
    ----------
    llm_client:
        An :class:`LLMClient` instance used for the Haiku decomposition call.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def decompose(
        self,
        query: str,
        classification: IntentClassification,
    ) -> list[SubQuery]:
        """Decompose a query into domain-specific sub-queries.

        If the classification indicates a multi-domain query (two or more
        domains scoring above :data:`MULTI_DOMAIN_THRESHOLD`), an LLM call
        decomposes the query.  Otherwise a single :class:`SubQuery` is
        returned targeting the primary domain.

        Parameters
        ----------
        query:
            The user's original natural language query.
        classification:
            The :class:`IntentClassification` produced by the intent router.

        Returns
        -------
        list[SubQuery]
            One or more sub-queries, each targeting a specific domain.
        """
        logger.debug(
            "QueryDecomposer.decompose() called — query=%r, is_multi_domain=%s",
            query,
            classification.is_multi_domain,
        )

        relevant_domains = self._get_relevant_domains(classification)

        # Single-domain: return the original query as-is
        if len(relevant_domains) < 2:
            sub_query = SubQuery(
                text=query,
                target_domain=classification.primary_domain,
                original_query=query,
            )
            logger.debug(
                "QueryDecomposer — single-domain, returning original query "
                "targeting %r",
                classification.primary_domain,
            )
            return [sub_query]

        # Multi-domain: use LLM to decompose
        return self._decompose_with_llm(query, relevant_domains)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_relevant_domains(
        classification: IntentClassification,
    ) -> list[str]:
        """Return domains that scored above MULTI_DOMAIN_THRESHOLD."""
        return [
            domain
            for domain, score in classification.domains.items()
            if score > MULTI_DOMAIN_THRESHOLD
        ]

    def _decompose_with_llm(
        self,
        query: str,
        relevant_domains: list[str],
    ) -> list[SubQuery]:
        """Call GPT-4o-mini to decompose the query into sub-queries.

        Falls back to returning the original query as a single SubQuery
        per relevant domain if the LLM call or JSON parsing fails.
        """
        domains_str = ", ".join(relevant_domains)
        prompt = (
            f"User query: {query}\n\n"
            f"Relevant domains: {domains_str}\n\n"
            "Decompose the query into sub-queries for each relevant domain."
        )

        logger.debug(
            "QueryDecomposer._decompose_with_llm() — calling LLM for "
            "domains=%s",
            domains_str,
        )

        try:
            raw_response = self._llm_client.classify(
                prompt=prompt,
                system=_DECOMPOSITION_SYSTEM_PROMPT,
            )
            sub_queries = self._parse_response(raw_response, query, relevant_domains)
            logger.info(
                "QueryDecomposer — decomposed into %d sub-queries",
                len(sub_queries),
            )
            return sub_queries

        except Exception:
            logger.exception(
                "QueryDecomposer._decompose_with_llm() failed — "
                "falling back to original query",
            )
            return self._fallback_sub_queries(query, relevant_domains)

    def _parse_response(
        self,
        raw: str,
        original_query: str,
        relevant_domains: list[str],
    ) -> list[SubQuery]:
        """Parse the LLM JSON response into a list of SubQuery objects.

        Handles common edge cases:
        * Strips markdown code fences if present.
        * Filters out sub-queries targeting domains not in the relevant set.
        * Falls back to the original query if parsing fails entirely.
        """
        cleaned = raw.strip()

        # Strip markdown code fences that LLMs sometimes add
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        parsed = json.loads(cleaned)

        if not isinstance(parsed, list):
            logger.warning(
                "QueryDecomposer._parse_response() — expected list, got %s; "
                "falling back",
                type(parsed).__name__,
            )
            return self._fallback_sub_queries(original_query, relevant_domains)

        sub_queries: list[SubQuery] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue

            text = item.get("text", "").strip()
            domain = item.get("domain", "").strip().lower()

            if not text or domain not in relevant_domains:
                continue

            sub_queries.append(
                SubQuery(
                    text=text,
                    target_domain=domain,
                    original_query=original_query,
                )
            )

        if not sub_queries:
            logger.warning(
                "QueryDecomposer._parse_response() — no valid sub-queries "
                "parsed; falling back",
            )
            return self._fallback_sub_queries(original_query, relevant_domains)

        return sub_queries

    @staticmethod
    def _fallback_sub_queries(
        query: str,
        relevant_domains: list[str],
    ) -> list[SubQuery]:
        """Create one SubQuery per relevant domain using the original query.

        This is the graceful fallback when LLM decomposition fails.
        """
        return [
            SubQuery(
                text=query,
                target_domain=domain,
                original_query=query,
            )
            for domain in relevant_domains
        ]
