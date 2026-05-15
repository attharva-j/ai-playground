"""LLM client for the ALO RAG generation engine.

Provides a unified wrapper around the OpenAI API with three calling modes:

- **generate()** — uses GPT-4o for high-quality answer generation
  with configurable ``max_tokens``. Synchronous; used by the eval harness.
- **generate_stream_async()** — uses GPT-4o with the AsyncOpenAI client
  to stream tokens as an async generator. Used by the interactive server
  endpoint so each token is flushed to the browser the instant it arrives.
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
_DEFAULT_GENERATION_MODEL = "gpt-4o-mini"
_DEFAULT_CLASSIFICATION_MODEL = "gpt-4.1-nano"

# Classification max_tokens is kept small — responses are short structured
# outputs (JSON with confidence scores, scope decisions, etc.).
_CLASSIFICATION_MAX_TOKENS = 80


class LLMClient:
    """Wrapper around the OpenAI API.

    Provides three calling modes optimised for different use-cases:

    * :meth:`generate` — GPT-4o-based synchronous generation for answer
      synthesis. Used by the eval harness. Supports a configurable
      ``max_tokens`` parameter (default 1024).
    * :meth:`generate_stream_async` — GPT-4o-based async streaming for the
      interactive server endpoint. Uses ``AsyncOpenAI`` so each token is
      yielded to the event loop immediately, enabling true token-by-token
      rendering in the browser without blocking.
    * :meth:`classify` — GPT-4.1-nano-based lightweight classification for
      intent routing and scope guard evaluation.  GPT-4.1-nano is OpenAI's
      fastest model and is well-suited to short structured-output tasks.
      Designed to return results within 1 second per query (R5.2).

    Two underlying OpenAI clients are lazily initialised on first use:
    ``openai.OpenAI`` for synchronous calls and ``openai.AsyncOpenAI``
    for async streaming.  Initialisation is deferred so that import-time
    failures (e.g. missing API key) do not prevent the class from loading.

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
        # Async client — lazy-initialised on first streaming call.
        self._async_client: Any | None = None

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

    async def generate_stream_async(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 512,
    ):
        """Stream a response token-by-token using GPT-4o via AsyncOpenAI.

        This is an **async generator** — it must be consumed with
        ``async for token in ...``.  Using ``AsyncOpenAI`` means each
        token is yielded back to the event loop the instant it arrives
        from the OpenAI API, enabling true real-time streaming to the
        browser without blocking FastAPI's event loop.

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
            Individual text chunks as they are generated by GPT-4o.
        """
        logger.debug(
            "LLMClient.generate_stream_async() called — model=%s, max_tokens=%d",
            self.model,
            max_tokens,
        )

        async_client = self._get_async_client()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        stream = await async_client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages,
            stream=True,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    def _get_async_client(self) -> Any:
        """Lazy-initialise and return the AsyncOpenAI client.

        Uses ``openai.AsyncOpenAI``, which is part of the same ``openai``
        package already installed.  The async client is required for
        non-blocking streaming inside FastAPI's async event loop.
        """
        if self._async_client is None:
            import openai  # noqa: WPS433

            self._async_client = openai.AsyncOpenAI()
            logger.info("AsyncOpenAI client initialised")
        return self._async_client

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
