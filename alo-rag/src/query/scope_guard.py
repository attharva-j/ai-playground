"""Scope guard for detecting out-of-scope queries in the ALO RAG System.

Evaluates whether ambiguous queries (all domain confidence scores below 0.3)
fall within the system's three knowledge domains (product, policy, customer)
or should be politely refused.  Uses GPT-4o-mini via :meth:`LLMClient.classify`
for lightweight scope evaluation.

Requirements: 11.1, 11.2, 11.3
"""

from __future__ import annotations

import json
import logging

from src.generation.llm_client import LLMClient
from src.models import IntentClassification, ScopeDecision

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for scope evaluation
# ---------------------------------------------------------------------------

_SCOPE_EVALUATION_SYSTEM_PROMPT: str = (
    "You are a scope evaluator for an ALO Yoga customer support system. "
    "The system can ONLY answer questions about:\n\n"
    "1. ALO Yoga products — specifications, materials, sizing, care instructions, "
    "fabric types, colours, pricing, or product comparisons.\n"
    "2. ALO Yoga policies — return policies, shipping SLAs, promotional eligibility "
    "rules, loyalty tier logic, or operational procedures.\n"
    "3. Customer orders — a specific customer's order history, loyalty status, "
    "past purchases, or account details.\n\n"
    "Given a user query, determine whether it falls within these three domains.\n\n"
    "Respond with ONLY a JSON object containing:\n"
    '- "is_in_scope": boolean — true if the query is about ALO Yoga products, '
    "policies, or customer orders, even if the intent is unclear.\n"
    '- "reason": string — a brief explanation of your decision.\n'
    '- "uncertainty_note": string or null — if the query IS in scope but '
    "ambiguous (could relate to multiple domains or the intent is unclear), "
    "provide a short note describing the ambiguity. Set to null if the query "
    "is clearly in scope or clearly out of scope.\n\n"
    "Examples:\n"
    '{"is_in_scope": false, "reason": "Query is about cooking recipes, unrelated to ALO Yoga.", "uncertainty_note": null}\n'
    '{"is_in_scope": true, "reason": "Query appears to be about clothing materials which could relate to ALO Yoga products.", "uncertainty_note": "This query is ambiguous — it may relate to ALO Yoga product materials, but the specific product is unclear."}\n'
    '{"is_in_scope": true, "reason": "Query is about yoga leggings sizing.", "uncertainty_note": null}\n\n'
    "Do not include any text outside the JSON object."
)

# ---------------------------------------------------------------------------
# Polite refusal message template
# ---------------------------------------------------------------------------

_REFUSAL_MESSAGE: str = (
    "I appreciate your question, but it falls outside the areas I can help with. "
    "I'm designed to assist with ALO Yoga products, store policies (returns, "
    "shipping, promotions, and loyalty programs), and customer order inquiries. "
    "If you have a question about any of these topics, I'd be happy to help!"
)


class ScopeGuard:
    """Evaluates whether ambiguous queries are in-scope or out-of-scope.

    When the Intent Router flags a query as ambiguous (all domain confidence
    scores below 0.3), the Scope Guard uses GPT-4o-mini to determine
    whether the query falls within the system's three knowledge domains.

    Three possible outcomes:

    * **Out-of-scope** — ``is_in_scope=False``, ``suggested_response`` contains
      a polite refusal message (R11.2).
    * **In-scope but ambiguous** — ``is_in_scope=True``, ``uncertainty_note``
      describes the ambiguity so the Generation Engine can append it to the
      answer (R11.3).
    * **Normal in-scope** — ``is_in_scope=True``, ``uncertainty_note=None``.

    Parameters
    ----------
    llm_client:
        An :class:`LLMClient` instance used for the Haiku classification call.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client

    def evaluate(
        self, query: str, classification: IntentClassification
    ) -> ScopeDecision:
        """Evaluate whether an ambiguous query is in-scope or out-of-scope.

        Calls GPT-4o-mini via :meth:`LLMClient.classify` and parses the
        JSON response into a :class:`ScopeDecision`.  If the LLM response
        cannot be parsed, defaults to in-scope with an uncertainty note
        (safer than refusing a potentially valid query).

        Parameters
        ----------
        query:
            The user's natural language query.
        classification:
            The intent classification result from the Intent Router.

        Returns
        -------
        ScopeDecision
            The scope evaluation result with one of three outcomes.
        """
        logger.debug(
            "ScopeGuard.evaluate() called — query=%r, is_ambiguous=%s",
            query,
            classification.is_ambiguous,
        )

        try:
            raw_response = self._llm_client.classify(
                prompt=query,
                system=_SCOPE_EVALUATION_SYSTEM_PROMPT,
            )
            return self._parse_response(raw_response)
        except Exception:
            logger.exception("ScopeGuard.evaluate() — LLM call or parsing failed")
            return self._safe_fallback()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_response(self, raw: str) -> ScopeDecision:
        """Parse the LLM JSON response into a :class:`ScopeDecision`.

        Handles common edge cases:
        * Strips markdown code fences if present.
        * Defaults to in-scope with uncertainty note on parse failure.
        """
        cleaned = raw.strip()

        # Strip markdown code fences that LLMs sometimes add
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        parsed = json.loads(cleaned)

        if not isinstance(parsed, dict):
            logger.warning(
                "ScopeGuard._parse_response() — expected dict, got %s",
                type(parsed).__name__,
            )
            return self._safe_fallback()

        is_in_scope = parsed.get("is_in_scope")
        if not isinstance(is_in_scope, bool):
            logger.warning(
                "ScopeGuard._parse_response() — is_in_scope not a bool: %r",
                is_in_scope,
            )
            return self._safe_fallback()

        reason = str(parsed.get("reason", ""))

        # Extract uncertainty_note (may be null/None or a string)
        raw_note = parsed.get("uncertainty_note")
        uncertainty_note = str(raw_note) if raw_note is not None else None

        if not is_in_scope:
            # Out-of-scope: generate polite refusal in code for consistency (R11.2)
            return ScopeDecision(
                is_in_scope=False,
                reason=reason,
                suggested_response=_REFUSAL_MESSAGE,
                uncertainty_note=None,
            )

        # In-scope: may or may not have an uncertainty note (R11.3)
        return ScopeDecision(
            is_in_scope=True,
            reason=reason,
            suggested_response=None,
            uncertainty_note=uncertainty_note,
        )

    @staticmethod
    def _safe_fallback() -> ScopeDecision:
        """Return a safe fallback decision when parsing fails.

        Defaults to in-scope with an uncertainty note — it is safer to
        attempt an answer with a caveat than to refuse a potentially
        valid query.
        """
        return ScopeDecision(
            is_in_scope=True,
            reason="Unable to determine scope; defaulting to in-scope.",
            suggested_response=None,
            uncertainty_note=(
                "I wasn't fully able to determine the scope of your question. "
                "The answer below is my best attempt, but it may not fully "
                "address your query."
            ),
        )
