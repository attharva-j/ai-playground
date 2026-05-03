"""Embedding service for the ALO RAG ingestion pipeline.

Provides dense vector embeddings with primary/fallback model support:
- Primary: Voyage AI voyage-3 (high-quality, requires API key)
- Fallback: sentence-transformers/all-mpnet-base-v2 (local, free)

Requirements: 3.1, 3.4
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Computes dense embeddings with primary/fallback model support.

    The primary model (voyage-3 via Voyage AI) is tried first.  If it
    is unavailable — due to a missing API key, network error, or any
    other exception — the service transparently falls back to a local
    sentence-transformers model (all-mpnet-base-v2) and logs the event.

    Parameters
    ----------
    primary_model:
        Voyage AI model identifier.  Defaults to ``"voyage-3"``.
    fallback_model:
        Hugging Face sentence-transformers model name.  Defaults to
        ``"all-mpnet-base-v2"``.
    """

    def __init__(
        self,
        primary_model: str = "voyage-3",
        fallback_model: str = "all-mpnet-base-v2",
    ) -> None:
        self.primary_model = primary_model
        self.fallback_model = fallback_model

        # Lazy-initialised clients — created on first use so that
        # import-time failures don't prevent the class from loading.
        self._voyage_client: Any | None = None
        self._st_model: Any | None = None
        self._using_fallback: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return dense embeddings for a batch of *texts*.

        Tries the primary model first; falls back to the local model on
        any failure.  Once the fallback is activated, all subsequent
        calls use the fallback to avoid embedding dimension mismatches
        between indexing and query time.
        """
        if not texts:
            return []

        # Once fallback is activated, stick with it to keep dimensions consistent
        if self._using_fallback:
            return self._use_fallback(texts)

        result = self._try_primary(texts)
        if result is not None:
            return result

        return self._use_fallback(texts)

    def embed_single(self, text: str) -> list[float]:
        """Return a dense embedding for a single *text* string."""
        results = self.embed([text])
        return results[0]

    # ------------------------------------------------------------------
    # Primary model (Voyage AI)
    # ------------------------------------------------------------------

    def _try_primary(self, texts: list[str]) -> list[list[float]] | None:
        """Attempt to embed *texts* using the Voyage AI primary model.

        Returns ``None`` on any failure so the caller can fall back.
        """
        try:
            client = self._get_voyage_client()
            response = client.embed(texts, model=self.primary_model)
            return [list(e) for e in response.embeddings]
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Primary embedding model (%s) unavailable, falling back "
                "to %s: %s",
                self.primary_model,
                self.fallback_model,
                exc,
            )
            return None

    def _get_voyage_client(self) -> Any:
        """Lazy-initialise and return the Voyage AI client."""
        if self._voyage_client is None:
            import voyageai  # noqa: WPS433

            self._voyage_client = voyageai.Client()
        return self._voyage_client

    # ------------------------------------------------------------------
    # Fallback model (sentence-transformers)
    # ------------------------------------------------------------------

    def _use_fallback(self, texts: list[str]) -> list[list[float]]:
        """Embed *texts* using the local sentence-transformers fallback model."""
        if not self._using_fallback:
            logger.info(
                "Switching to fallback embedding model: %s",
                self.fallback_model,
            )
            self._using_fallback = True

        model = self._get_st_model()
        embeddings = model.encode(texts, show_progress_bar=False)
        return [e.tolist() for e in embeddings]

    def _get_st_model(self) -> Any:
        """Lazy-initialise and return the sentence-transformers model."""
        if self._st_model is None:
            from sentence_transformers import SentenceTransformer  # noqa: WPS433

            self._st_model = SentenceTransformer(self.fallback_model)
        return self._st_model
