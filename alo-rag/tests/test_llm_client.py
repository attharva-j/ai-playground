"""Unit tests for the LLM client module."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.generation.llm_client import (
    LLMClient,
    _CLASSIFICATION_MAX_TOKENS,
    _DEFAULT_CLASSIFICATION_MODEL,
    _DEFAULT_GENERATION_MODEL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_response(text: str) -> SimpleNamespace:
    """Build a minimal object that mimics an OpenAI ChatCompletion response."""
    message = SimpleNamespace(content=text)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestLLMClientInit:
    """Tests for LLMClient initialisation and defaults."""

    def test_default_models(self) -> None:
        client = LLMClient()
        assert client.model == _DEFAULT_GENERATION_MODEL
        assert client.classification_model == _DEFAULT_CLASSIFICATION_MODEL

    def test_custom_models(self) -> None:
        client = LLMClient(model="custom-gpt", classification_model="custom-mini")
        assert client.model == "custom-gpt"
        assert client.classification_model == "custom-mini"

    def test_lazy_client_not_created_at_init(self) -> None:
        client = LLMClient()
        assert client._client is None


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------


class TestGenerate:
    """Tests for LLMClient.generate()."""

    def test_generate_returns_text(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response(
            "Generated answer"
        )
        client._client = mock_openai_client

        result = client.generate("What is the return policy?")

        assert result == "Generated answer"

    def test_generate_uses_gpt4o_model(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response("ok")
        client._client = mock_openai_client

        client.generate("test prompt")

        call_kwargs = mock_openai_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == _DEFAULT_GENERATION_MODEL

    def test_generate_passes_max_tokens(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response("ok")
        client._client = mock_openai_client

        client.generate("test", max_tokens=2048)

        call_kwargs = mock_openai_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["max_tokens"] == 2048

    def test_generate_default_max_tokens_is_1024(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response("ok")
        client._client = mock_openai_client

        client.generate("test")

        call_kwargs = mock_openai_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["max_tokens"] == 1024

    def test_generate_includes_system_when_provided(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response("ok")
        client._client = mock_openai_client

        client.generate("test", system="You are a helpful assistant.")

        call_kwargs = mock_openai_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "You are a helpful assistant."}
        assert messages[1] == {"role": "user", "content": "test"}

    def test_generate_omits_system_when_empty(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response("ok")
        client._client = mock_openai_client

        client.generate("test", system="")

        call_kwargs = mock_openai_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_generate_sends_user_message(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response("ok")
        client._client = mock_openai_client

        client.generate("Hello world")

        call_kwargs = mock_openai_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "Hello world"

    def test_generate_raises_on_api_error(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = RuntimeError("API down")
        client._client = mock_openai_client

        with pytest.raises(RuntimeError, match="API down"):
            client.generate("test")


# ---------------------------------------------------------------------------
# classify()
# ---------------------------------------------------------------------------


class TestClassify:
    """Tests for LLMClient.classify()."""

    def test_classify_returns_text(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response(
            '{"product": 0.9}'
        )
        client._client = mock_openai_client

        result = client.classify("What are the leggings made of?")

        assert result == '{"product": 0.9}'

    def test_classify_uses_mini_model(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response("ok")
        client._client = mock_openai_client

        client.classify("test")

        call_kwargs = mock_openai_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == _DEFAULT_CLASSIFICATION_MODEL

    def test_classify_uses_small_max_tokens(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response("ok")
        client._client = mock_openai_client

        client.classify("test")

        call_kwargs = mock_openai_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["max_tokens"] == _CLASSIFICATION_MAX_TOKENS

    def test_classify_includes_system_when_provided(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response("ok")
        client._client = mock_openai_client

        client.classify("test", system="Classify the query.")

        call_kwargs = mock_openai_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "Classify the query."}

    def test_classify_omits_system_when_empty(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response("ok")
        client._client = mock_openai_client

        client.classify("test")

        call_kwargs = mock_openai_client.chat.completions.create.call_args
        messages = call_kwargs.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"

    def test_classify_raises_on_api_error(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = RuntimeError("timeout")
        client._client = mock_openai_client

        with pytest.raises(RuntimeError, match="timeout"):
            client.classify("test")


# ---------------------------------------------------------------------------
# Lazy client initialisation
# ---------------------------------------------------------------------------


class TestLazyInit:
    """Tests for lazy OpenAI client initialisation."""

    @patch("src.generation.llm_client.openai", create=True)
    def test_client_created_on_first_call(self, mock_openai_module: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_instance.chat.completions.create.return_value = _make_mock_response("ok")
        mock_openai_module.OpenAI.return_value = mock_instance

        client = LLMClient()
        # Patch the import inside _get_client
        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            client.generate("test")

        mock_openai_module.OpenAI.assert_called_once()

    def test_client_reused_across_calls(self) -> None:
        client = LLMClient()
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _make_mock_response("ok")
        client._client = mock_openai_client

        client.generate("first call")
        client.classify("second call")

        # Both calls should use the same underlying client
        assert mock_openai_client.chat.completions.create.call_count == 2
