"""Faithfulness guardrail for the ALO RAG generation engine.

Verifies that every factual claim in a generated answer is traceable to
the provided context chunks.  When unsupported claims are detected, a
single regeneration attempt is made with a stricter prompt.  If the
regenerated answer still contains unsupported claims it is returned as-is
with the issues flagged.

Requirements: 10.1, 10.2, 10.3, 10.4
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.generation.llm_client import LLMClient
from src.models import Claim, FaithfulnessResult, FaithfulnessStatus, RetrievedChunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_VERIFY_SYSTEM = """\
You are a faithfulness auditor.  Your job is to verify whether each factual
claim in an AI-generated answer is supported by the provided context chunks.

For each claim, determine:
- Whether it is SUPPORTED (directly traceable to a context chunk) or
  UNSUPPORTED (not found in any context chunk).
- If supported, which chunk ID supports it.

Respond with a JSON object in this exact format (no markdown fences):
{
  "claims": [
    {
      "text": "<the claim text>",
      "supported": true,
      "supporting_chunk_id": "<chunk_id or null>"
    }
  ]
}
"""

_VERIFY_USER_TEMPLATE = """\
## Context Chunks

{context}

## Generated Answer

{answer}

Extract every factual claim from the generated answer and verify each one
against the context chunks above.  Return the JSON object as specified.
"""

_REGENERATE_SYSTEM = """\
You are an ALO Yoga customer support assistant.  Answer the user's question
using ONLY the information explicitly stated in the context chunks below.

STRICT RULES:
1. Do NOT include any information that is not directly stated in the context.
2. If the context does not contain enough information, say so honestly.
3. Cite the chunk ID in square brackets for every factual claim, e.g. [ALO-LEG-001].
4. Do NOT infer, extrapolate, or add information from general knowledge.
"""

_REGENERATE_USER_TEMPLATE = """\
## Context Chunks

{context}

## User Query

{query}

Answer the query using ONLY the context above.  Cite chunk IDs for every claim.
"""


class FaithfulnessGuardrail:
    """Verifies generated answers against source context via a second LLM call.

    If unsupported claims are found, triggers one regeneration attempt using
    a stricter prompt.  The regenerated answer becomes the final answer
    regardless of whether it fully resolves the issues — no further
    regeneration attempts are made (R10.2, R10.3).

    Parameters
    ----------
    llm_client:
        The :class:`LLMClient` used for verification and regeneration calls.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify(
        self,
        answer: str,
        context_chunks: list[RetrievedChunk],
        query: str = "",
    ) -> FaithfulnessResult:
        """Verify *answer* against *context_chunks* and optionally regenerate.

        Parameters
        ----------
        answer:
            The generated answer to verify.
        context_chunks:
            The retrieval results that were used as context for generation.
        query:
            The original user query (needed for regeneration if triggered).

        Returns
        -------
        FaithfulnessResult
            Contains the faithfulness score, claim-level details, and
            regeneration status.
        """
        context_text = self._render_context(context_chunks)

        # -- Step 1: Extract and verify claims --------------------------------
        claims = self._extract_and_verify_claims(answer, context_text)

        # Handle verification error — fail closed
        if claims is None:
            logger.warning("FaithfulnessGuardrail: verification error — failing closed")
            return FaithfulnessResult(
                score=0.0,
                claims=[],
                unsupported_claims=[],
                regeneration_triggered=False,
                regenerated_answer=None,
                status=FaithfulnessStatus.FAILED_VERIFICATION_ERROR,
            )

        # Handle no context
        if not context_chunks:
            return FaithfulnessResult(
                score=0.0,
                claims=claims,
                unsupported_claims=claims,
                regeneration_triggered=False,
                regenerated_answer=None,
                status=FaithfulnessStatus.FAILED_NO_CONTEXT,
            )

        unsupported = [c for c in claims if not c.supported]

        if not unsupported:
            score = 1.0
            logger.debug(
                "FaithfulnessGuardrail: all %d claims supported — score=%.2f",
                len(claims),
                score,
            )
            return FaithfulnessResult(
                score=score,
                claims=claims,
                unsupported_claims=[],
                regeneration_triggered=False,
                regenerated_answer=None,
                status=FaithfulnessStatus.PASSED,
            )

        # -- Step 2: Regenerate with stricter prompt --------------------------
        logger.info(
            "FaithfulnessGuardrail: %d/%d claims unsupported — triggering regeneration",
            len(unsupported),
            len(claims),
        )

        regenerated_answer = self._regenerate(query, context_chunks)

        # -- Step 3: Re-verify the regenerated answer -------------------------
        regen_claims = self._extract_and_verify_claims(
            regenerated_answer, context_text
        )

        if regen_claims is None:
            return FaithfulnessResult(
                score=0.0,
                claims=[],
                unsupported_claims=[],
                regeneration_triggered=True,
                regenerated_answer=regenerated_answer,
                status=FaithfulnessStatus.FAILED_VERIFICATION_ERROR,
            )

        regen_unsupported = [c for c in regen_claims if not c.supported]

        total = len(regen_claims) if regen_claims else 1
        supported_count = total - len(regen_unsupported)
        score = supported_count / total

        if regen_unsupported:
            logger.warning(
                "FaithfulnessGuardrail: regenerated answer still has %d "
                "unsupported claims — returning as-is with flags (score=%.2f)",
                len(regen_unsupported),
                score,
            )
        else:
            logger.debug(
                "FaithfulnessGuardrail: regeneration resolved all issues — score=%.2f",
                score,
            )

        status = (
            FaithfulnessStatus.PASSED if not regen_unsupported
            else FaithfulnessStatus.FAILED_UNSUPPORTED
        )

        return FaithfulnessResult(
            score=score,
            claims=regen_claims,
            unsupported_claims=regen_unsupported,
            regeneration_triggered=True,
            regenerated_answer=regenerated_answer,
            status=status,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_and_verify_claims(
        self,
        answer: str,
        context_text: str,
    ) -> list[Claim] | None:
        """Use the LLM to extract claims and verify each one.

        Returns None when verification failed technically, e.g. malformed JSON
        or LLM exception. The caller must fail closed in that case.
        """
        prompt = _VERIFY_USER_TEMPLATE.format(
            context=context_text,
            answer=answer,
        )

        try:
            raw_response = self._llm.generate(
                prompt=prompt,
                system=_VERIFY_SYSTEM,
                max_tokens=2048,
            )
            return self._parse_claims(raw_response)
        except Exception:
            logger.exception("FaithfulnessGuardrail: claim extraction failed")
            return None


    @staticmethod
    def _parse_claims(raw_response: str) -> list[Claim] | None:
        """Parse the LLM's JSON response into Claim objects.

        Malformed JSON returns None, not [], because [] is interpreted as
        'no factual claims' and can incorrectly pass faithfulness.
        """
        text = raw_response.strip()

        if text.startswith("```"):
            lines = [
                line
                for line in text.splitlines()
                if not line.strip().startswith("```")
            ]
            text = "\n".join(lines).strip()

        try:
            data: dict[str, Any] = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(
                "FaithfulnessGuardrail: failed to parse claims JSON. Raw response: %s",
                raw_response[:300],
            )
            return None

        raw_claims = data.get("claims")
        if raw_claims is None or not isinstance(raw_claims, list):
            logger.warning(
                "FaithfulnessGuardrail: JSON missing claims list. Raw response: %s",
                raw_response[:300],
            )
            return None

        claims: list[Claim] = []
        for entry in raw_claims:
            if not isinstance(entry, dict):
                continue
            claims.append(
                Claim(
                    text=str(entry.get("text", "")),
                    supported=bool(entry.get("supported", False)),
                    supporting_chunk_id=entry.get("supporting_chunk_id"),
                )
            )

        return claims

    def _regenerate(
        self,
        query: str,
        context_chunks: list[RetrievedChunk],
    ) -> str:
        """Regenerate the answer with a stricter prompt (R10.2).

        Only one regeneration attempt is made.  The result is returned
        regardless of quality.
        """
        context_text = self._render_context(context_chunks)
        prompt = _REGENERATE_USER_TEMPLATE.format(
            context=context_text,
            query=query,
        )

        try:
            return self._llm.generate(
                prompt=prompt,
                system=_REGENERATE_SYSTEM,
                max_tokens=1024,
            )
        except Exception:
            logger.exception(
                "FaithfulnessGuardrail: regeneration failed — returning empty string"
            )
            return ""

    @staticmethod
    def _render_context(chunks: list[RetrievedChunk]) -> str:
        """Render context chunks as a text block for the verification prompt."""
        if not chunks:
            return "No context chunks provided."

        parts: list[str] = []
        for rc in chunks:
            chunk = rc.chunk
            parts.append(
                f"[{chunk.chunk_id}] (score: {rc.score:.3f})\n{chunk.text}"
            )
        return "\n\n".join(parts)
