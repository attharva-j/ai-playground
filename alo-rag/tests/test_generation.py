"""Unit tests for the generation components.

Covers:
- CustomerContextInjector returns correct profile for valid ID and None for unknown ID
- PromptBuilder includes all required sections in rendered prompt
- FaithfulnessGuardrail detects unsupported claims and triggers regeneration
- Regeneration limit (max one attempt)

Requirements: 4.1, 4.2, 4.3, 9.1, 10.1, 10.2, 10.3, 10.4
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.generation.customer_context import CustomerContextInjector
from src.generation.guardrails import FaithfulnessGuardrail
from src.generation.prompt_builder import PromptBuilder
from src.models import (
    Chunk,
    ChunkMetadata,
    CustomerProfile,
    Order,
    OrderItem,
    RetrievedChunk,
    FaithfulnessStatus,
)


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_SAMPLE_CUSTOMERS_DATA = {
    "customers": [
        {
            "customer_id": "CUST-001",
            "name": "Sarah Chen",
            "email": "sarah.chen@example.com",
            "loyalty_tier": "gold",
            "orders": [
                {
                    "order_id": "ORD-2024-001",
                    "date": "2024-01-15",
                    "status": "delivered",
                    "total": 236.00,
                    "items": [
                        {
                            "product_id": "ALO-LEG-001",
                            "product_name": "Airlift High-Waist Legging",
                            "quantity": 2,
                            "price": 118.00,
                            "size": "S",
                            "was_discounted": False,
                            "discount_pct": 0,
                            "final_sale": False,
                        }
                    ],
                }
            ],
        },
        {
            "customer_id": "CUST-002",
            "name": "James Park",
            "email": "james.park@example.com",
            "loyalty_tier": "silver",
            "orders": [
                {
                    "order_id": "ORD-2024-010",
                    "date": "2024-03-20",
                    "status": "delivered",
                    "total": 89.00,
                    "items": [
                        {
                            "product_id": "ALO-TOP-005",
                            "product_name": "Alosoft Crop Tank",
                            "quantity": 1,
                            "price": 62.00,
                            "size": "M",
                            "was_discounted": True,
                            "discount_pct": 30,
                            "final_sale": True,
                        },
                        {
                            "product_id": "ALO-ACC-002",
                            "product_name": "Yoga Mat",
                            "quantity": 1,
                            "price": 27.00,
                            "size": "",
                            "was_discounted": False,
                            "discount_pct": 0,
                            "final_sale": False,
                        },
                    ],
                }
            ],
        },
    ]
}


def _write_customers_json(tmp_dir: Path, data: dict | None = None) -> Path:
    """Write customer data to a temp JSON file and return the path."""
    path = tmp_dir / "customers.json"
    path.write_text(json.dumps(data or _SAMPLE_CUSTOMERS_DATA), encoding="utf-8")
    return path


def _make_chunk(
    chunk_id: str,
    text: str = "sample text",
    domain: str = "product",
    **meta_kwargs,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        metadata=ChunkMetadata(domain=domain, **meta_kwargs),
        source_document="source.json",
    )


def _make_rc(
    chunk_id: str,
    text: str = "sample text",
    score: float = 0.85,
    source: str = "reranked",
    domain: str = "product",
    **meta_kwargs,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=_make_chunk(chunk_id, text=text, domain=domain, **meta_kwargs),
        score=score,
        source=source,
    )


def _make_customer_profile() -> CustomerProfile:
    """Build a CustomerProfile in-memory for tests that don't need file I/O."""
    return CustomerProfile(
        customer_id="CUST-001",
        name="Sarah Chen",
        email="sarah.chen@example.com",
        loyalty_tier="gold",
        orders=[
            Order(
                order_id="ORD-2024-001",
                date="2024-01-15",
                items=[
                    OrderItem(
                        product_id="ALO-LEG-001",
                        product_name="Airlift High-Waist Legging",
                        quantity=2,
                        price=118.00,
                        size="S",
                        was_discounted=False,
                        discount_pct=0,
                        final_sale=False,
                    )
                ],
                status="delivered",
                total=236.00,
            )
        ],
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. CustomerContextInjector (R4.1, R4.2, R4.3)
# ═══════════════════════════════════════════════════════════════════════════


class TestCustomerContextInjectorValidLookup:
    """Test that get_customer returns the correct profile for a valid ID."""

    def test_returns_profile_for_valid_id(self, tmp_path: Path) -> None:
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        profile = injector.get_customer("CUST-001")

        assert profile is not None
        assert profile.customer_id == "CUST-001"
        assert profile.name == "Sarah Chen"

    def test_profile_has_correct_email(self, tmp_path: Path) -> None:
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        profile = injector.get_customer("CUST-001")

        assert profile is not None
        assert profile.email == "sarah.chen@example.com"

    def test_profile_has_correct_loyalty_tier(self, tmp_path: Path) -> None:
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        profile = injector.get_customer("CUST-002")

        assert profile is not None
        assert profile.loyalty_tier == "silver"

    def test_profile_contains_complete_order_history(self, tmp_path: Path) -> None:
        """R4.2: get_customer returns the complete order history."""
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        profile = injector.get_customer("CUST-001")

        assert profile is not None
        assert len(profile.orders) == 1
        order = profile.orders[0]
        assert order.order_id == "ORD-2024-001"
        assert order.date == "2024-01-15"
        assert order.status == "delivered"
        assert order.total == 236.00

    def test_order_items_parsed_correctly(self, tmp_path: Path) -> None:
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        profile = injector.get_customer("CUST-001")

        assert profile is not None
        item = profile.orders[0].items[0]
        assert item.product_id == "ALO-LEG-001"
        assert item.product_name == "Airlift High-Waist Legging"
        assert item.quantity == 2
        assert item.price == 118.00
        assert item.size == "S"
        assert item.was_discounted is False
        assert item.discount_pct == 0
        assert item.final_sale is False

    def test_discounted_and_final_sale_items(self, tmp_path: Path) -> None:
        """Verify was_discounted, discount_pct, and final_sale fields."""
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        profile = injector.get_customer("CUST-002")

        assert profile is not None
        item = profile.orders[0].items[0]
        assert item.was_discounted is True
        assert item.discount_pct == 30
        assert item.final_sale is True

    def test_multiple_items_in_order(self, tmp_path: Path) -> None:
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        profile = injector.get_customer("CUST-002")

        assert profile is not None
        assert len(profile.orders[0].items) == 2


class TestCustomerContextInjectorUnknownId:
    """Test that get_customer returns None for unknown IDs (R4.3)."""

    def test_returns_none_for_unknown_id(self, tmp_path: Path) -> None:
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        assert injector.get_customer("CUST-999") is None

    def test_returns_none_for_empty_string_id(self, tmp_path: Path) -> None:
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        assert injector.get_customer("") is None

    def test_returns_none_for_none_like_id(self, tmp_path: Path) -> None:
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        assert injector.get_customer("None") is None


class TestCustomerContextInjectorListCustomers:
    """Test list_customers returns sorted customer IDs."""

    def test_list_customers_returns_all_ids(self, tmp_path: Path) -> None:
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        ids = injector.list_customers()

        assert set(ids) == {"CUST-001", "CUST-002"}

    def test_list_customers_sorted(self, tmp_path: Path) -> None:
        path = _write_customers_json(tmp_path)
        injector = CustomerContextInjector(data_path=path)

        ids = injector.list_customers()

        assert ids == sorted(ids)

    def test_list_customers_empty_when_no_data(self, tmp_path: Path) -> None:
        path = _write_customers_json(tmp_path, data={"customers": []})
        injector = CustomerContextInjector(data_path=path)

        assert injector.list_customers() == []


class TestCustomerContextInjectorEdgeCases:
    """Edge cases: missing file, malformed JSON, etc."""

    def test_missing_file_loads_no_profiles(self, tmp_path: Path) -> None:
        path = tmp_path / "nonexistent.json"
        injector = CustomerContextInjector(data_path=path)

        assert injector.list_customers() == []
        assert injector.get_customer("CUST-001") is None

    def test_malformed_json_loads_no_profiles(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{invalid json", encoding="utf-8")
        injector = CustomerContextInjector(data_path=path)

        assert injector.list_customers() == []

    def test_missing_optional_fields_use_defaults(self, tmp_path: Path) -> None:
        """Customer with minimal fields should still load with defaults."""
        data = {
            "customers": [
                {
                    "customer_id": "CUST-MINIMAL",
                    "orders": [],
                }
            ]
        }
        path = _write_customers_json(tmp_path, data=data)
        injector = CustomerContextInjector(data_path=path)

        profile = injector.get_customer("CUST-MINIMAL")

        assert profile is not None
        assert profile.name == ""
        assert profile.email == ""
        assert profile.loyalty_tier == ""
        assert profile.orders == []


# ═══════════════════════════════════════════════════════════════════════════
# 2. PromptBuilder (R9.1, R9.3)
# ═══════════════════════════════════════════════════════════════════════════


class TestPromptBuilderRequiredSections:
    """Verify the rendered prompt includes all required sections."""

    def test_rendered_contains_retrieved_context_section(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("ALO-LEG-001", text="Airlift legging details")]

        prompt = builder.build("What are the leggings made of?", chunks)

        assert "## Retrieved Context" in prompt.rendered

    def test_rendered_contains_user_query_section(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("ALO-LEG-001")]

        prompt = builder.build("What are the leggings made of?", chunks)

        assert "## User Query" in prompt.rendered
        assert "What are the leggings made of?" in prompt.rendered

    def test_rendered_contains_chunk_ids(self) -> None:
        builder = PromptBuilder()
        chunks = [
            _make_rc("ALO-LEG-001", text="Legging info"),
            _make_rc("ALO-TOP-003", text="Top info"),
        ]

        prompt = builder.build("query", chunks)

        assert "ALO-LEG-001" in prompt.rendered
        assert "ALO-TOP-003" in prompt.rendered

    def test_rendered_contains_relevance_scores(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("ALO-LEG-001", score=0.923)]

        prompt = builder.build("query", chunks)

        assert "0.923" in prompt.rendered

    def test_rendered_contains_chunk_text(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("c1", text="Nylon and spandex blend fabric")]

        prompt = builder.build("query", chunks)

        assert "Nylon and spandex blend fabric" in prompt.rendered

    def test_rendered_contains_metadata(self) -> None:
        builder = PromptBuilder()
        chunks = [
            _make_rc("c1", domain="product", product_id="ALO-LEG-001", category="leggings")
        ]

        prompt = builder.build("query", chunks)

        assert "domain=product" in prompt.rendered
        assert "product_id=ALO-LEG-001" in prompt.rendered
        assert "category=leggings" in prompt.rendered

    def test_rendered_contains_policy_metadata(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("pol1", domain="policy", policy_type="returns")]

        prompt = builder.build("query", chunks)

        assert "domain=policy" in prompt.rendered
        assert "policy_type=returns" in prompt.rendered


class TestPromptBuilderCustomerContext:
    """Verify customer context is included when provided."""

    def test_customer_context_section_present(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("c1")]
        customer = _make_customer_profile()

        prompt = builder.build("query", chunks, customer_context=customer)

        assert "## Customer Context" in prompt.rendered

    def test_customer_name_and_id_in_prompt(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("c1")]
        customer = _make_customer_profile()

        prompt = builder.build("query", chunks, customer_context=customer)

        assert "Sarah Chen" in prompt.rendered
        assert "CUST-001" in prompt.rendered

    def test_customer_loyalty_tier_in_prompt(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("c1")]
        customer = _make_customer_profile()

        prompt = builder.build("query", chunks, customer_context=customer)

        assert "gold" in prompt.rendered

    def test_order_history_in_prompt(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("c1")]
        customer = _make_customer_profile()

        prompt = builder.build("query", chunks, customer_context=customer)

        assert "ORD-2024-001" in prompt.rendered
        assert "2024-01-15" in prompt.rendered
        assert "delivered" in prompt.rendered

    def test_order_items_in_prompt(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("c1")]
        customer = _make_customer_profile()

        prompt = builder.build("query", chunks, customer_context=customer)

        assert "Airlift High-Waist Legging" in prompt.rendered

    def test_no_customer_context_section_when_none(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("c1")]

        prompt = builder.build("query", chunks, customer_context=None)

        assert "## Customer Context" not in prompt.rendered


class TestPromptBuilderSystemMessage:
    """Verify the system message is set correctly."""

    def test_system_message_is_non_empty(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build("query", [_make_rc("c1")])

        assert len(prompt.system_message) > 0

    def test_system_message_instructs_citation(self) -> None:
        """System message should instruct the LLM to cite chunk IDs."""
        builder = PromptBuilder()
        prompt = builder.build("query", [_make_rc("c1")])

        assert "chunk" in prompt.system_message.lower() or "cite" in prompt.system_message.lower()


class TestPromptBuilderDataclassFields:
    """Verify the GenerationPrompt dataclass fields are populated."""

    def test_context_chunks_stored(self) -> None:
        builder = PromptBuilder()
        chunks = [_make_rc("c1"), _make_rc("c2")]

        prompt = builder.build("query", chunks)

        assert prompt.context_chunks == chunks

    def test_query_stored(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build("What is the return policy?", [_make_rc("c1")])

        assert prompt.query == "What is the return policy?"

    def test_customer_context_stored(self) -> None:
        builder = PromptBuilder()
        customer = _make_customer_profile()

        prompt = builder.build("query", [_make_rc("c1")], customer_context=customer)

        assert prompt.customer_context is customer

    def test_customer_context_none_when_not_provided(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build("query", [_make_rc("c1")])

        assert prompt.customer_context is None

    def test_empty_chunks_shows_no_context_message(self) -> None:
        builder = PromptBuilder()
        prompt = builder.build("query", [])

        assert "No relevant context was found" in prompt.rendered


# ═══════════════════════════════════════════════════════════════════════════
# 3. FaithfulnessGuardrail (R10.1, R10.2, R10.3, R10.4)
# ═══════════════════════════════════════════════════════════════════════════


def _claims_json(claims: list[dict]) -> str:
    """Build a JSON string matching the guardrail's expected format."""
    return json.dumps({"claims": claims})


class TestFaithfulnessGuardrailAllSupported:
    """When all claims are supported, no regeneration should occur."""

    def test_score_is_1_when_all_supported(self) -> None:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = _claims_json([
            {"text": "Leggings are made of nylon", "supported": True, "supporting_chunk_id": "c1"},
            {"text": "They come in size S-XL", "supported": True, "supporting_chunk_id": "c1"},
        ])

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        chunks = [_make_rc("c1", text="Nylon leggings, sizes S-XL")]

        result = guardrail.verify("Leggings are nylon, sizes S-XL", chunks)

        assert result.score == 1.0

    def test_no_regeneration_when_all_supported(self) -> None:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = _claims_json([
            {"text": "claim", "supported": True, "supporting_chunk_id": "c1"},
        ])

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("answer", [_make_rc("c1")])

        assert result.regeneration_triggered is False
        assert result.regenerated_answer is None

    def test_no_unsupported_claims(self) -> None:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = _claims_json([
            {"text": "claim", "supported": True, "supporting_chunk_id": "c1"},
        ])

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("answer", [_make_rc("c1")])

        assert result.unsupported_claims == []

    def test_claims_list_populated(self) -> None:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = _claims_json([
            {"text": "Claim A", "supported": True, "supporting_chunk_id": "c1"},
            {"text": "Claim B", "supported": True, "supporting_chunk_id": "c2"},
        ])

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("answer", [_make_rc("c1"), _make_rc("c2")])

        assert len(result.claims) == 2
        assert all(c.supported for c in result.claims)

    def test_llm_called_once_when_all_supported(self) -> None:
        """Only the verification call should be made — no regeneration."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = _claims_json([
            {"text": "claim", "supported": True, "supporting_chunk_id": "c1"},
        ])

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        guardrail.verify("answer", [_make_rc("c1")])

        # Only 1 call: the verification call
        assert mock_llm.generate.call_count == 1


class TestFaithfulnessGuardrailUnsupportedClaims:
    """When unsupported claims are found, regeneration should trigger (R10.2)."""

    def _setup_guardrail_with_unsupported(
        self,
        regen_claims_supported: bool = True,
    ) -> tuple[FaithfulnessGuardrail, MagicMock]:
        """Set up a guardrail where the first verify finds unsupported claims,
        then regeneration produces a new answer, and re-verification either
        passes or fails based on regen_claims_supported."""
        mock_llm = MagicMock()

        # First call: verification — finds unsupported claim
        first_verify = _claims_json([
            {"text": "Leggings are nylon", "supported": True, "supporting_chunk_id": "c1"},
            {"text": "They are made in Italy", "supported": False, "supporting_chunk_id": None},
        ])

        # Second call: regeneration — returns a new answer
        regenerated_answer = "The Airlift leggings are made of nylon and spandex [c1]."

        # Third call: re-verification of regenerated answer
        if regen_claims_supported:
            regen_verify = _claims_json([
                {"text": "Airlift leggings are nylon and spandex", "supported": True, "supporting_chunk_id": "c1"},
            ])
        else:
            regen_verify = _claims_json([
                {"text": "Airlift leggings are nylon", "supported": True, "supporting_chunk_id": "c1"},
                {"text": "They are eco-friendly", "supported": False, "supporting_chunk_id": None},
            ])

        mock_llm.generate.side_effect = [first_verify, regenerated_answer, regen_verify]

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        return guardrail, mock_llm

    def test_regeneration_triggered(self) -> None:
        guardrail, _ = self._setup_guardrail_with_unsupported()
        chunks = [_make_rc("c1", text="Nylon and spandex leggings")]

        result = guardrail.verify("Leggings are nylon, made in Italy", chunks, query="query")

        assert result.regeneration_triggered is True

    def test_regenerated_answer_returned(self) -> None:
        guardrail, _ = self._setup_guardrail_with_unsupported()
        chunks = [_make_rc("c1", text="Nylon and spandex leggings")]

        result = guardrail.verify("Leggings are nylon, made in Italy", chunks, query="query")

        assert result.regenerated_answer is not None
        assert "nylon and spandex" in result.regenerated_answer.lower()

    def test_score_reflects_regenerated_answer(self) -> None:
        """Score should be based on the regenerated answer, not the original."""
        guardrail, _ = self._setup_guardrail_with_unsupported(regen_claims_supported=True)
        chunks = [_make_rc("c1")]

        result = guardrail.verify("bad answer", chunks, query="query")

        assert result.score == 1.0

    def test_llm_called_three_times(self) -> None:
        """Verify → regenerate → re-verify = 3 LLM calls."""
        guardrail, mock_llm = self._setup_guardrail_with_unsupported()
        chunks = [_make_rc("c1")]

        guardrail.verify("bad answer", chunks, query="query")

        assert mock_llm.generate.call_count == 3


class TestFaithfulnessGuardrailRegenerationLimit:
    """R10.3: Only one regeneration attempt; if still unsupported, return as-is."""

    def test_max_one_regeneration_attempt(self) -> None:
        """Even if regenerated answer has unsupported claims, no further
        regeneration should occur — exactly 3 LLM calls total."""
        mock_llm = MagicMock()

        # First verify: unsupported claim found
        first_verify = _claims_json([
            {"text": "Made in Italy", "supported": False, "supporting_chunk_id": None},
        ])
        # Regeneration: new answer
        regenerated = "Still a problematic answer."
        # Re-verify: still has unsupported claim
        second_verify = _claims_json([
            {"text": "Still problematic", "supported": False, "supporting_chunk_id": None},
        ])

        mock_llm.generate.side_effect = [first_verify, regenerated, second_verify]

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        chunks = [_make_rc("c1")]

        result = guardrail.verify("bad answer", chunks, query="query")

        # Exactly 3 calls: verify, regenerate, re-verify — no more
        assert mock_llm.generate.call_count == 3

    def test_unsupported_claims_flagged_after_failed_regeneration(self) -> None:
        """When regeneration doesn't fix issues, unsupported claims are flagged."""
        mock_llm = MagicMock()

        first_verify = _claims_json([
            {"text": "Hallucinated claim", "supported": False, "supporting_chunk_id": None},
        ])
        regenerated = "Another answer with issues."
        second_verify = _claims_json([
            {"text": "Good claim", "supported": True, "supporting_chunk_id": "c1"},
            {"text": "Still hallucinated", "supported": False, "supporting_chunk_id": None},
        ])

        mock_llm.generate.side_effect = [first_verify, regenerated, second_verify]

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("bad", [_make_rc("c1")], query="q")

        assert len(result.unsupported_claims) == 1
        assert result.unsupported_claims[0].text == "Still hallucinated"

    def test_score_reflects_remaining_issues(self) -> None:
        """Score should reflect the proportion of supported claims after regen."""
        mock_llm = MagicMock()

        first_verify = _claims_json([
            {"text": "bad", "supported": False, "supporting_chunk_id": None},
        ])
        regenerated = "new answer"
        # 1 supported, 1 unsupported → score = 0.5
        second_verify = _claims_json([
            {"text": "good", "supported": True, "supporting_chunk_id": "c1"},
            {"text": "bad", "supported": False, "supporting_chunk_id": None},
        ])

        mock_llm.generate.side_effect = [first_verify, regenerated, second_verify]

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("bad", [_make_rc("c1")], query="q")

        assert result.score == pytest.approx(0.5)

    def test_regeneration_triggered_flag_set(self) -> None:
        """regeneration_triggered should be True even if regen didn't fix it."""
        mock_llm = MagicMock()

        first_verify = _claims_json([
            {"text": "bad", "supported": False, "supporting_chunk_id": None},
        ])
        regenerated = "new answer"
        second_verify = _claims_json([
            {"text": "still bad", "supported": False, "supporting_chunk_id": None},
        ])

        mock_llm.generate.side_effect = [first_verify, regenerated, second_verify]

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("bad", [_make_rc("c1")], query="q")

        assert result.regeneration_triggered is True


class TestFaithfulnessGuardrailScoreComputation:
    """R10.4: Score is proportion of supported claims (0.0 to 1.0)."""

    def test_score_1_when_all_supported(self) -> None:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = _claims_json([
            {"text": "a", "supported": True, "supporting_chunk_id": "c1"},
            {"text": "b", "supported": True, "supporting_chunk_id": "c1"},
            {"text": "c", "supported": True, "supporting_chunk_id": "c2"},
        ])

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("answer", [_make_rc("c1"), _make_rc("c2")])

        assert result.score == 1.0

    def test_score_1_when_no_claims_extracted(self) -> None:
        """If the LLM returns no claims, score defaults to 1.0."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = _claims_json([])

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("answer", [_make_rc("c1")])

        assert result.score == 1.0


class TestFaithfulnessGuardrailClaimParsing:
    """Test that the guardrail correctly parses LLM claim responses."""

    def test_parses_claims_with_markdown_fences(self) -> None:
        """LLM may wrap JSON in markdown code fences — should still parse."""
        mock_llm = MagicMock()
        fenced_json = '```json\n' + _claims_json([
            {"text": "claim", "supported": True, "supporting_chunk_id": "c1"},
        ]) + '\n```'
        mock_llm.generate.return_value = fenced_json

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("answer", [_make_rc("c1")])

        assert len(result.claims) == 1
        assert result.claims[0].supported is True

    def test_handles_malformed_json_fails_closed(self) -> None:
        """If LLM returns invalid JSON, verification should fail closed."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "This is not JSON at all"

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("answer", [_make_rc("c1")])

        assert result.claims == []
        assert result.score == 0.0
        assert result.status == FaithfulnessStatus.FAILED_VERIFICATION_ERROR

    def test_handles_llm_exception_gracefully(self) -> None:
        """If the LLM call raises, should fail closed (not crash)."""
        mock_llm = MagicMock()
        mock_llm.generate.side_effect = RuntimeError("API error")

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("answer", [_make_rc("c1")])

        assert result.claims == []
        assert result.score == 0.0  # fail closed on verification error


class TestFaithfulnessGuardrailContextRendering:
    """Verify that context chunks are rendered correctly for the LLM."""

    def test_empty_context_handled(self) -> None:
        mock_llm = MagicMock()
        mock_llm.generate.return_value = _claims_json([])

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        result = guardrail.verify("answer", [])

        # Should not crash; returns a valid result (fail closed — no context)
        assert result.score == 0.0

    def test_verification_prompt_includes_answer(self) -> None:
        """The verification LLM call should include the answer text."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = _claims_json([])

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        guardrail.verify("The leggings are made of nylon", [_make_rc("c1")])

        call_args = mock_llm.generate.call_args
        prompt = call_args.kwargs.get("prompt") or call_args[0][0]
        assert "The leggings are made of nylon" in prompt

    def test_verification_prompt_includes_chunk_text(self) -> None:
        """The verification LLM call should include the context chunk text."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = _claims_json([])

        guardrail = FaithfulnessGuardrail(llm_client=mock_llm)
        guardrail.verify("answer", [_make_rc("c1", text="Nylon and spandex blend")])

        call_args = mock_llm.generate.call_args
        prompt = call_args.kwargs.get("prompt") or call_args[0][0]
        assert "Nylon and spandex blend" in prompt
