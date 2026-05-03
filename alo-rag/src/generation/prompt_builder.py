"""Prompt builder for the ALO RAG generation engine.

Constructs structured prompts from retrieved context chunks, optional
customer data, and the user query.  The assembled prompt is designed to
guide the LLM toward accurate, well-sourced answers that reference
specific chunks.

Requirements: 9.1, 9.3
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.models import CustomerProfile, RetrievedChunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------

_SYSTEM_MESSAGE = """\
You are an ALO Yoga customer support assistant.  Answer the user's question
using the information provided in the context sections below.

Rules:
1. Base every factual claim on a specific context chunk or the customer data.
   Cite chunk IDs in square brackets, e.g. [ALO-LEG-001]. When referencing
   customer order data, cite [customer:<customer_id>].
2. Provide thorough, detailed answers.  Include specific details like fabric
   compositions, percentages, measurements, prices, and policy specifics
   when they appear in the context.
3. When comparing products or fabrics, list the key differences point by point
   using the details from each relevant chunk.
4. If the context does not contain enough information to fully answer, provide
   what you can from the context and note what is missing.
5. IMPORTANT — When customer order data is provided in the "Customer Context"
   section, you MUST lead your answer with the customer-specific details:
   - Reference the customer by name
   - Cite their specific order IDs, item names, order dates, and statuses
   - Apply policy rules to their specific situation (e.g. if their item is
     Final Sale, state that explicitly with the item name and discount)
   - Combine customer data with policy information to give a complete,
     personalised answer — do not just quote policy in the abstract
6. Format answers with clear structure — use bullet points or numbered lists
   for comparisons and multi-part answers.
"""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class GenerationPrompt:
    """A fully assembled prompt ready for LLM generation.

    Attributes
    ----------
    system_message:
        The system-level instructions for the LLM.
    context_chunks:
        The ranked retrieval results included as context.
    customer_context:
        Optional customer profile for personalisation.
    query:
        The original user query.
    rendered:
        The final assembled prompt string sent to the LLM as the user
        message.
    """

    system_message: str
    context_chunks: list[RetrievedChunk]
    customer_context: CustomerProfile | None
    query: str
    rendered: str


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


class PromptBuilder:
    """Constructs structured prompts from retrieved context and customer data.

    The builder assembles four sections into a single user-message string:

    1. **Retrieved context** — each chunk with its ID and relevance score.
    2. **Customer context** — order history and loyalty tier (if provided).
    3. **User query** — the original natural-language question.

    The system message is returned separately so the caller can pass it
    via the ``system`` parameter of the LLM client.
    """

    def build(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        customer_context: CustomerProfile | None = None,
    ) -> GenerationPrompt:
        """Build a :class:`GenerationPrompt` from the given inputs.

        Parameters
        ----------
        query:
            The user's natural-language question.
        chunks:
            Ranked retrieval results to include as context.
        customer_context:
            Optional customer profile for personalisation.

        Returns
        -------
        GenerationPrompt
            The fully assembled prompt with system message and rendered
            user message.
        """
        sections: list[str] = []

        # -- Retrieved context ------------------------------------------------
        sections.append(self._render_context_chunks(chunks))

        # -- Customer context (optional) --------------------------------------
        if customer_context is not None:
            sections.append(self._render_customer_context(customer_context))

        # -- User query -------------------------------------------------------
        sections.append(f"## User Query\n\n{query}")

        rendered = "\n\n".join(sections)

        logger.debug(
            "PromptBuilder: assembled prompt — %d chunks, customer=%s, %d chars",
            len(chunks),
            customer_context.customer_id if customer_context else "none",
            len(rendered),
        )

        return GenerationPrompt(
            system_message=_SYSTEM_MESSAGE,
            context_chunks=chunks,
            customer_context=customer_context,
            query=query,
            rendered=rendered,
        )

    # ------------------------------------------------------------------
    # Internal rendering helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _render_context_chunks(chunks: list[RetrievedChunk]) -> str:
        """Render retrieved chunks as a numbered context section."""
        if not chunks:
            return "## Retrieved Context\n\nNo relevant context was found."

        lines: list[str] = ["## Retrieved Context\n"]
        for idx, rc in enumerate(chunks, start=1):
            chunk = rc.chunk
            header = (
                f"### Chunk {idx} — [{chunk.chunk_id}] "
                f"(relevance: {rc.score:.3f}, source: {rc.source})"
            )
            metadata_parts: list[str] = [f"domain={chunk.metadata.domain}"]
            if chunk.metadata.product_id:
                metadata_parts.append(f"product_id={chunk.metadata.product_id}")
            if chunk.metadata.category:
                metadata_parts.append(f"category={chunk.metadata.category}")
            if chunk.metadata.policy_type:
                metadata_parts.append(f"policy_type={chunk.metadata.policy_type}")

            metadata_line = "Metadata: " + ", ".join(metadata_parts)

            lines.append(header)
            lines.append(metadata_line)
            lines.append("")  # blank line before text
            lines.append(chunk.text)
            lines.append("")  # blank line after chunk

        return "\n".join(lines)

    @staticmethod
    def _render_customer_context(profile: CustomerProfile) -> str:
        """Render customer profile and order history as a context section."""
        lines: list[str] = [
            "## Customer Context\n",
            f"**Customer:** {profile.name} ({profile.customer_id})",
            f"**Email:** {profile.email}",
            f"**Loyalty Tier:** {profile.loyalty_tier}",
        ]

        if profile.orders:
            lines.append(f"\n**Order History** ({len(profile.orders)} orders):\n")
            for order in profile.orders:
                lines.append(
                    f"- **{order.order_id}** | {order.date} | "
                    f"status: {order.status} | total: ${order.total:.2f}"
                )
                for item in order.items:
                    discount_info = ""
                    if item.was_discounted:
                        discount_info = f" ({item.discount_pct}% off)"
                    final_sale_info = " [FINAL SALE]" if item.final_sale else ""
                    lines.append(
                        f"  - {item.product_name} (size {item.size}) "
                        f"× {item.quantity} @ ${item.price:.2f}"
                        f"{discount_info}{final_sale_info}"
                    )
        else:
            lines.append("\nNo order history available.")

        return "\n".join(lines)
