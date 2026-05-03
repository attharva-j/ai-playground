"""Hypothetical Document Embeddings (HyDE) module for the ALO RAG System.

Generates a hypothetical answer document for policy queries using the LLM,
then embeds that hypothetical answer for use in dense retrieval instead of
the raw query embedding.  This bridges the vocabulary gap between abstract
user questions and the terminology used in policy documents.

The hypothetical document is generated using GPT-4o-mini (via
LLMClient.classify()) rather than GPT-4o.  The document is never shown
to the user — it is only embedded for retrieval.  The quality requirement
is vocabulary richness and domain register, not reasoning correctness.
GPT-4o-mini meets this bar at roughly 500ms less latency per call.

Requirements: 6.1, 6.2, 6.3
"""

from __future__ import annotations

import logging

from src.generation.llm_client import LLMClient
from src.ingestion.embedders import EmbeddingService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for hypothetical answer generation
# ---------------------------------------------------------------------------

_HYDE_SYSTEM_PROMPT: str = (
    "You are an ALO Yoga policy document author. Given a customer question, "
    "write a short, plausible excerpt from an ALO Yoga policy document that "
    "would directly answer the question. Write as if you are quoting from the "
    "official ALO Yoga policy documentation — use specific details, conditions, "
    "timeframes, and eligibility rules that a real policy document would contain.\n\n"
    "Guidelines:\n"
    "- Write 2-4 sentences in a formal policy document style.\n"
    "- Include specific numbers (days, percentages, dollar amounts) where relevant.\n"
    "- Reference policy concepts like return windows, shipping tiers, loyalty "
    "benefits, or promotional eligibility as appropriate.\n"
    "- Do NOT include any preamble or explanation — output only the policy excerpt."
)


class HyDEModule:
    """Generates hypothetical answer documents for improved policy retrieval.

    When a user asks an abstract policy question (e.g. "What's the return
    window for sale items?"), the raw query embedding may not match the
    terminology in the actual policy documents.  HyDE generates a
    *hypothetical* answer first, then embeds that answer.  The resulting
    embedding is closer in vector space to the real policy chunks,
    improving dense retrieval recall.

    The module does **not** decide when to activate — that decision is
    made by the pipeline orchestrator based on the intent classification
    (policy domain confidence > 0.5).  This module simply generates and
    embeds when called.

    Parameters
    ----------
    llm_client:
        An :class:`LLMClient` instance used for hypothetical answer
        generation. Uses the classify() path (GPT-4o-mini) rather than
        generate() (GPT-4o) — the hypothetical is for embedding only,
        not for display, so the faster model is appropriate.
    embedding_service:
        An :class:`EmbeddingService` instance used to embed the
        hypothetical answer.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        embedding_service: EmbeddingService,
    ) -> None:
        self._llm_client = llm_client
        self._embedding_service = embedding_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_hypothetical(self, query: str) -> str:
        """Generate a hypothetical policy document excerpt for the query.

        Uses GPT-4o-mini via :meth:`LLMClient.classify` to produce a
        plausible policy document excerpt that would answer the user's
        question.  This hypothetical answer is intended to be embedded
        for dense retrieval, not returned to the user.  GPT-4o-mini is
        used (rather than GPT-4o) because the document is evaluated only
        by its embedding proximity to real policy chunks — vocabulary
        richness matters, not reasoning depth.

        Parameters
        ----------
        query:
            The user's natural language policy question.

        Returns
        -------
        str
            A hypothetical policy document excerpt.

        Raises
        ------
        Exception
            Re-raised after logging if the LLM call fails.
        """
        logger.debug(
            "HyDEModule.generate_hypothetical() called — query=%r", query,
        )

        try:
            # Use classify() (GPT-4o-mini) rather than generate() (GPT-4o).
            # The hypothetical document is embedded for retrieval only — it
            # is never shown to the user.  Vocabulary richness matters;
            # reasoning quality does not.  GPT-4o-mini is ~500ms faster
            # for this output length.
            hypothetical = self._llm_client.classify(
                prompt=query,
                system=_HYDE_SYSTEM_PROMPT,
                max_tokens=200,
            )
            logger.info(
                "HyDEModule.generate_hypothetical() completed — %d chars",
                len(hypothetical),
            )
            return hypothetical

        except Exception:
            logger.exception(
                "HyDEModule.generate_hypothetical() failed — query=%r",
                query,
            )
            raise

    def embed_hypothetical(self, hypothetical: str) -> list[float]:
        """Embed a hypothetical answer for use in dense retrieval.

        Uses :meth:`EmbeddingService.embed_single` to compute a dense
        vector embedding of the hypothetical answer.  This embedding
        replaces the raw query embedding in the retrieval step (R6.2).

        Parameters
        ----------
        hypothetical:
            The hypothetical policy document excerpt to embed.

        Returns
        -------
        list[float]
            Dense vector embedding of the hypothetical answer.

        Raises
        ------
        Exception
            Re-raised after logging if the embedding call fails.
        """
        logger.debug(
            "HyDEModule.embed_hypothetical() called — %d chars",
            len(hypothetical),
        )

        try:
            embedding = self._embedding_service.embed_single(hypothetical)
            logger.info(
                "HyDEModule.embed_hypothetical() completed — %d dimensions",
                len(embedding),
            )
            return embedding

        except Exception:
            logger.exception("HyDEModule.embed_hypothetical() failed")
            raise

    def process(self, query: str) -> list[float]:
        """Generate a hypothetical answer and return its embedding.

        Orchestrates the full HyDE flow:

        1. Generate a hypothetical policy document excerpt via the LLM.
        2. Embed the hypothetical answer.
        3. Return the embedding for use in dense retrieval.

        Parameters
        ----------
        query:
            The user's natural language policy question.

        Returns
        -------
        list[float]
            Dense vector embedding of the hypothetical answer.

        Raises
        ------
        Exception
            Re-raised after logging if any step fails.
        """
        logger.debug("HyDEModule.process() called — query=%r", query)

        hypothetical = self.generate_hypothetical(query)
        embedding = self.embed_hypothetical(hypothetical)

        logger.info(
            "HyDEModule.process() completed — hypothetical=%r",
            hypothetical[:120] + "..." if len(hypothetical) > 120 else hypothetical,
        )

        return embedding
