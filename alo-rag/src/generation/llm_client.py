"""LLM client for the ALO RAG generation engine.

Provides a unified wrapper around the OpenAI API with two calling modes:

- **generate()** — uses GPT-4o for high-quality answer generation
  with configurable ``max_tokens``.
- **classify()** — uses GPT-4.1-nano for fast, lightweight classification
  tasks such as intent routing and scope guard evaluation. GPT-4.1-nano
  is chosen over gpt-4o-mini for its lower latency and cost on short
  structured-output tasks (classification, decomposition, scope guard).

Requirements: 5.1, 5.2, 9.2
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default model identifiers
_DEFAULT_GENERATION_MODEL = "gpt-4o"
_DEFAULT_CLASSIFICATION_MODEL = "gpt-4.1-nano"

# Classification max_tokens is kept small — responses are short structured
# outputs (JSON with confidence scores, scope decisions, etc.).
_CLASSIFICATION_MAX_TOKENS = 80


class LLMClient:
    """Wrapper around the OpenAI API.

    Provides two calling modes optimised for different use-cases:

    * :meth:`generate` — GPT-4o-based generation for answer synthesis.
      Supports a configurable ``max_tokens`` parameter (default 1024).
    * :meth:`classify` — GPT-4.1-nano-based lightweight classification for
      intent routing and scope guard evaluation.  GPT-4.1-nano is OpenAI's
      fastest model and is well-suited to short structured-output tasks.
      Designed to return results within 1 second per query (R5.2).

    The underlying ``openai.OpenAI`` client is lazily initialised
    on first use so that import-time failures (e.g. missing API key) do
    not prevent the class from loading.

    Parameters
    ----------
    model:
        OpenAI model identifier used for generation calls.
        Defaults to ``"gpt-4o"``.
    classification_model:
        OpenAI model identifier used for classification calls.
        Defaults to ``"gpt-4.1-nano"``.
    """

    def __init__(
        self,
        model: str = _DEFAULT_GENERATION_MODEL,
        classification_model: str = _DEFAULT_CLASSIFICATION_MODEL,
    ) -> None:
        self.model = model
        self.classification_model = classification_model

        # Lazy-initialised — created on first API call.
        self._client: Any | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
    ) -> str:
        """Generate a response using GPT-4o.

        This is the primary generation method used by the Generation
        Engine to produce answers from retrieved context (R9.2).

        Parameters
        ----------
        prompt:
            The user-facing prompt / message content.
        system:
            Optional system message providing instructions and context.
        max_tokens:
            Maximum number of tokens in the generated response.

        Returns
        -------
        str
            The text content of the model's response.

        Raises
        ------
        openai.APIError
            Re-raised after logging if the OpenAI API returns an error.
        """
        logger.debug(
            "LLMClient.generate() called — model=%s, max_tokens=%d",
            self.model,
            max_tokens,
        )

        try:
            client = self._get_client()
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=messages,
            )
            text = response.choices[0].message.content
            logger.debug(
                "LLMClient.generate() completed — %d chars returned",
                len(text),
            )
            return text

        except Exception:
            logger.exception(
                "LLMClient.generate() failed — model=%s",
                self.model,
            )
            raise

    def generate_stream(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
    ):
        """Stream a response token-by-token using GPT-4o.

        Yields text chunks as they arrive from the OpenAI API, enabling
        real-time token-by-token rendering on the frontend.

        Parameters
        ----------
        prompt:
            The user-facing prompt / message content.
        system:
            Optional system message providing instructions and context.
        max_tokens:
            Maximum number of tokens in the generated response.

        Yields
        ------
        str
            Individual text chunks as they are generated.
        """
        logger.debug(
            "LLMClient.generate_stream() called — model=%s, max_tokens=%d",
            self.model,
            max_tokens,
        )

        client = self._get_client()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        stream = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    def classify(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = _CLASSIFICATION_MAX_TOKENS,
    ) -> str:
        """Lightweight classification call using GPT-4.1-nano.

        Used by the Intent Router (R5.1) and Scope Guard (R11.1) for
        fast query classification.  GPT-4.1-nano is chosen for its low
        latency on short structured-output tasks, keeping classification
        within the 1-second budget (R5.2).

        Parameters
        ----------
        prompt:
            The user-facing prompt / message content.
        system:
            Optional system message providing classification instructions.
        max_tokens:
            Maximum number of tokens in the response. Defaults to 80
            for classification tasks; callers like HyDE can pass a
            higher value (e.g. 200) for longer structured outputs.

        Returns
        -------
        str
            The text content of the model's response.

        Raises
        ------
        openai.APIError
            Re-raised after logging if the OpenAI API returns an error.
        """
        logger.debug(
            "LLMClient.classify() called — model=%s",
            self.classification_model,
        )

        try:
            client = self._get_client()
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.classification_model,
                max_tokens=max_tokens,
                messages=messages,
            )
            text = response.choices[0].message.content
            logger.debug(
                "LLMClient.classify() completed — %d chars returned",
                len(text),
            )
            return text

        except Exception:
            logger.exception(
                "LLMClient.classify() failed — model=%s",
                self.classification_model,
            )
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Lazy-initialise and return the OpenAI client.

        The client reads ``OPENAI_API_KEY`` from the environment
        automatically.  Initialisation is deferred so that the module
        can be imported without requiring the key at import time.
        """
        if self._client is None:
            import openai  # noqa: WPS433

            self._client = openai.OpenAI()
            logger.info("OpenAI client initialised")
        return self._client
