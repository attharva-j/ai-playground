"""Unit tests for the HyDE module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.query.hyde import HyDEModule, _HYDE_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_hyde_module(
    classify_return: str = "Hypothetical policy excerpt.",
    embed_return: list[float] | None = None,
) -> tuple[HyDEModule, MagicMock, MagicMock]:
    """Create a HyDEModule with mocked LLMClient and EmbeddingService."""
    mock_llm = MagicMock()
    mock_llm.classify.return_value = classify_return

    mock_embedder = MagicMock()
    mock_embedder.embed_single.return_value = embed_return or [0.1, 0.2, 0.3]

    module = HyDEModule(llm_client=mock_llm, embedding_service=mock_embedder)
    return module, mock_llm, mock_embedder


# ---------------------------------------------------------------------------
# generate_hypothetical()
# ---------------------------------------------------------------------------


class TestGenerateHypothetical:
    """Tests for HyDEModule.generate_hypothetical()."""

    def test_returns_llm_generated_text(self) -> None:
        module, mock_llm, _ = _make_hyde_module(
            classify_return="Items purchased at 30% or more off are final sale.",
        )

        result = module.generate_hypothetical("Can I return sale items?")

        assert result == "Items purchased at 30% or more off are final sale."

    def test_calls_llm_classify_with_query(self) -> None:
        module, mock_llm, _ = _make_hyde_module()

        module.generate_hypothetical("What is the return window?")

        mock_llm.classify.assert_called_once_with(
            prompt="What is the return window?",
            system=_HYDE_SYSTEM_PROMPT,
            max_tokens=200,
        )

    def test_uses_hyde_system_prompt(self) -> None:
        module, mock_llm, _ = _make_hyde_module()

        module.generate_hypothetical("test query")

        call_kwargs = mock_llm.classify.call_args
        system = call_kwargs.kwargs["system"]
        assert "ALO Yoga" in system
        assert "policy document" in system

    def test_raises_on_llm_failure(self) -> None:
        module, mock_llm, _ = _make_hyde_module()
        mock_llm.classify.side_effect = RuntimeError("LLM unavailable")

        with pytest.raises(RuntimeError, match="LLM unavailable"):
            module.generate_hypothetical("test query")


# ---------------------------------------------------------------------------
# embed_hypothetical()
# ---------------------------------------------------------------------------


class TestEmbedHypothetical:
    """Tests for HyDEModule.embed_hypothetical()."""

    def test_returns_embedding_vector(self) -> None:
        module, _, mock_embedder = _make_hyde_module(
            embed_return=[0.5, 0.6, 0.7, 0.8],
        )

        result = module.embed_hypothetical("Some hypothetical answer text.")

        assert result == [0.5, 0.6, 0.7, 0.8]

    def test_calls_embed_single_with_hypothetical_text(self) -> None:
        module, _, mock_embedder = _make_hyde_module()

        module.embed_hypothetical("ALO Yoga returns are accepted within 30 days.")

        mock_embedder.embed_single.assert_called_once_with(
            "ALO Yoga returns are accepted within 30 days.",
        )

    def test_raises_on_embedding_failure(self) -> None:
        module, _, mock_embedder = _make_hyde_module()
        mock_embedder.embed_single.side_effect = RuntimeError("Embedding service down")

        with pytest.raises(RuntimeError, match="Embedding service down"):
            module.embed_hypothetical("test text")


# ---------------------------------------------------------------------------
# process()
# ---------------------------------------------------------------------------


class TestProcess:
    """Tests for HyDEModule.process() — the full orchestration flow."""

    def test_returns_embedding_of_hypothetical(self) -> None:
        module, _, _ = _make_hyde_module(
            classify_return="Returns are accepted within 30 days of purchase.",
            embed_return=[0.11, 0.22, 0.33],
        )

        result = module.process("What is the return policy?")

        assert result == [0.11, 0.22, 0.33]

    def test_generates_then_embeds(self) -> None:
        """Verify process() calls classify first, then embed with the result."""
        module, mock_llm, mock_embedder = _make_hyde_module(
            classify_return="Free shipping on orders over $75.",
            embed_return=[1.0, 2.0],
        )

        module.process("Do you offer free shipping?")

        # LLM classify was called with the original query
        mock_llm.classify.assert_called_once()
        assert mock_llm.classify.call_args.kwargs["prompt"] == "Do you offer free shipping?"

        # Embedder was called with the hypothetical output, not the query
        mock_embedder.embed_single.assert_called_once_with(
            "Free shipping on orders over $75.",
        )

    def test_raises_when_generation_fails(self) -> None:
        module, mock_llm, _ = _make_hyde_module()
        mock_llm.classify.side_effect = RuntimeError("generation error")

        with pytest.raises(RuntimeError, match="generation error"):
            module.process("test query")

    def test_raises_when_embedding_fails(self) -> None:
        module, _, mock_embedder = _make_hyde_module()
        mock_embedder.embed_single.side_effect = RuntimeError("embedding error")

        with pytest.raises(RuntimeError, match="embedding error"):
            module.process("test query")

    def test_does_not_embed_when_generation_fails(self) -> None:
        """If generation fails, embed should not be called."""
        module, mock_llm, mock_embedder = _make_hyde_module()
        mock_llm.classify.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            module.process("test query")

        mock_embedder.embed_single.assert_not_called()
