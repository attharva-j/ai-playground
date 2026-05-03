"""Evaluation metrics for the ALO RAG System.

Provides two metric classes:

- **RetrievalMetrics** — standard IR metrics (Recall@k, MRR, Context
  Precision) computed from retrieved chunk IDs vs. ground-truth relevant
  chunk IDs.
- **GenerationMetrics** — LLM-as-judge metrics (Faithfulness, Answer
  Relevance) and a suite-level Hallucination Rate.

Requirements: 14.1, 14.2, 14.3, 15.1, 15.2, 15.3
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.generation.llm_client import LLMClient
    from src.models import EvalResult

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Retrieval Metrics (R14.1, R14.2, R14.3)
# ═══════════════════════════════════════════════════════════════════════════


class RetrievalMetrics:
    """Standard information-retrieval metrics computed from chunk ID lists."""

    @staticmethod
    def recall_at_k(
        retrieved_ids: list[str],
        relevant_ids: list[str],
        k: int = 5,
    ) -> float:
        """Proportion of relevant chunks appearing in the top-*k* results.

        Parameters
        ----------
        retrieved_ids:
            Ordered list of chunk IDs returned by the retrieval engine.
        relevant_ids:
            Ground-truth set of relevant chunk IDs for the query.
        k:
            Number of top results to consider.

        Returns
        -------
        float
            Recall score between 0.0 and 1.0.  Returns 0.0 when
            *relevant_ids* is empty.
        """
        if not relevant_ids:
            return 0.0

        top_k = set(retrieved_ids[:k])
        relevant = set(relevant_ids)
        hits = top_k & relevant
        return len(hits) / len(relevant)

    @staticmethod
    def mrr(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
        """Mean Reciprocal Rank — reciprocal of the rank of the first
        relevant chunk in the retrieved list.

        Parameters
        ----------
        retrieved_ids:
            Ordered list of chunk IDs returned by the retrieval engine.
        relevant_ids:
            Ground-truth set of relevant chunk IDs for the query.

        Returns
        -------
        float
            MRR score between 0.0 and 1.0.  Returns 0.0 when no
            relevant chunk appears in *retrieved_ids*.
        """
        relevant = set(relevant_ids)
        for rank, chunk_id in enumerate(retrieved_ids, start=1):
            if chunk_id in relevant:
                return 1.0 / rank
        return 0.0

    @staticmethod
    def context_precision(
        retrieved_ids: list[str],
        relevant_ids: list[str],
    ) -> float:
        """Proportion of retrieved chunks that are relevant (precision).

        Parameters
        ----------
        retrieved_ids:
            Ordered list of chunk IDs returned by the retrieval engine.
        relevant_ids:
            Ground-truth set of relevant chunk IDs for the query.

        Returns
        -------
        float
            Precision score between 0.0 and 1.0.  Returns 0.0 when
            *retrieved_ids* is empty.
        """
        if not retrieved_ids:
            return 0.0

        relevant = set(relevant_ids)
        hits = sum(1 for cid in retrieved_ids if cid in relevant)
        return hits / len(retrieved_ids)


# ═══════════════════════════════════════════════════════════════════════════
# Generation Metrics (R15.1, R15.2, R15.3)
# ═══════════════════════════════════════════════════════════════════════════

_FAITHFULNESS_SYSTEM = """\
You are an impartial evaluator. Given a generated answer and a list of \
context passages, determine what proportion of factual claims in the \
answer are supported by the context.

Respond with ONLY a JSON object in this exact format:
{"score": <float between 0.0 and 1.0>, "reasoning": "<brief explanation>"}

Scoring guide:
- 1.0 = every factual claim is fully supported by the context
- 0.0 = no factual claims are supported by the context
- Intermediate values reflect the proportion of supported claims
"""

_FAITHFULNESS_PROMPT = """\
## Context passages
{context}

## Generated answer
{answer}

Evaluate the faithfulness of the answer to the context passages. \
Return your evaluation as JSON."""

_RELEVANCE_SYSTEM = """\
You are an impartial evaluator. Given a user query and a generated \
answer, determine how well the answer addresses the original question.

Respond with ONLY a JSON object in this exact format:
{"score": <float between 0.0 and 1.0>, "reasoning": "<brief explanation>"}

Scoring guide:
- 1.0 = the answer fully and directly addresses the query
- 0.0 = the answer is completely irrelevant to the query
- Intermediate values reflect partial relevance
"""

_RELEVANCE_PROMPT = """\
## User query
{query}

## Generated answer
{answer}

Evaluate how well the answer addresses the query. Return your evaluation as JSON."""


class GenerationMetrics:
    """LLM-as-judge generation quality metrics.

    Uses a secondary LLM call to evaluate faithfulness and answer
    relevance.  Also provides a static method for computing the
    suite-level hallucination rate.

    Parameters
    ----------
    llm_client:
        An :class:`LLMClient` instance used for LLM-as-judge calls.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    def faithfulness(self, answer: str, context: list[str]) -> float:
        """Evaluate faithfulness of *answer* against *context* passages.

        Uses an LLM-as-judge call to score how well the answer's claims
        are supported by the provided context (R15.1).

        Returns
        -------
        float
            Score between 0.0 and 1.0.
        """
        context_text = "\n\n---\n\n".join(
            f"[Passage {i + 1}]\n{c}" for i, c in enumerate(context)
        )
        prompt = _FAITHFULNESS_PROMPT.format(context=context_text, answer=answer)

        try:
            raw = self._llm.classify(prompt=prompt, system=_FAITHFULNESS_SYSTEM)
            return self._parse_score(raw)
        except Exception:
            logger.exception("GenerationMetrics.faithfulness() — LLM call failed")
            return 0.0

    def answer_relevance(self, answer: str, query: str) -> float:
        """Evaluate how well *answer* addresses the original *query*.

        Uses an LLM-as-judge call to score answer-to-query alignment
        (R15.2).

        Returns
        -------
        float
            Score between 0.0 and 1.0.
        """
        prompt = _RELEVANCE_PROMPT.format(query=query, answer=answer)

        try:
            raw = self._llm.classify(prompt=prompt, system=_RELEVANCE_SYSTEM)
            return self._parse_score(raw)
        except Exception:
            logger.exception("GenerationMetrics.answer_relevance() — LLM call failed")
            return 0.0

    @staticmethod
    def hallucination_rate(results: list[EvalResult]) -> float:
        """Proportion of answers containing at least one unsupported claim.

        Defined as the fraction of :class:`EvalResult` entries where
        ``has_hallucination`` is ``True`` (R15.3).

        Parameters
        ----------
        results:
            List of per-query evaluation results.

        Returns
        -------
        float
            Rate between 0.0 and 1.0.  Returns 0.0 for an empty list.
        """
        if not results:
            return 0.0
        hallucinated = sum(1 for r in results if r.has_hallucination)
        return hallucinated / len(results)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_score(raw_response: str) -> float:
        """Extract a numeric score from the LLM's JSON response.

        Falls back to 0.0 if parsing fails.
        """
        try:
            # Strip markdown code fences if present
            text = raw_response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()

            data = json.loads(text)
            score = float(data.get("score", 0.0))
            return max(0.0, min(1.0, score))
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning(
                "GenerationMetrics._parse_score() — failed to parse: %r (%s)",
                raw_response[:200],
                exc,
            )
            return 0.0
