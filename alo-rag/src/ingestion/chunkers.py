"""Domain-specific chunkers for the ALO RAG ingestion pipeline.

- ProductChunker: one chunk per product, concatenating all product fields.
- PolicyChunker: semantic section-based chunking that preserves conditional
  logic blocks (if/then/else rules) intact within a single chunk.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from src.models import Chunk, ChunkMetadata, RawDocument

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ingestion summary
# ---------------------------------------------------------------------------


@dataclass
class ChunkingSummary:
    """Counts of records processed during a chunking run."""

    total_records: int = 0
    ingested: int = 0
    skipped: int = 0


# ---------------------------------------------------------------------------
# Product chunker
# ---------------------------------------------------------------------------


class ProductChunker:
    """Creates one :class:`Chunk` per product from a :class:`RawDocument`.

    The ``RawDocument.metadata`` dict is expected to contain the full
    product JSON object (as produced by :class:`ProductLoader`).  Each
    product is validated for required fields before chunking.
    """

    REQUIRED_FIELDS: tuple[str, ...] = ("product_id", "name", "description")
    # The actual data catalog may use "sku" instead of "product_id".
    FIELD_ALIASES: dict[str, str] = {"product_id": "sku"}

    def chunk(self, documents: list[RawDocument]) -> tuple[list[Chunk], ChunkingSummary]:
        """Chunk a list of product :class:`RawDocument` instances.

        Returns a tuple of ``(chunks, summary)`` where *summary* reports
        how many records were ingested vs. skipped.
        """
        chunks: list[Chunk] = []
        summary = ChunkingSummary()

        for doc_index, doc in enumerate(documents):
            summary.total_records += 1
            product: dict[str, Any] = doc.metadata

            # Handle fabric glossary entries (entity_type == "fabric")
            if product.get("entity_type") == "fabric":
                chunk_id = product.get("chunk_id", f"fabric-{product.get('fabric_name', 'unknown').lower()}")
                chunk = Chunk(
                    chunk_id=chunk_id,
                    text=doc.content,
                    metadata=ChunkMetadata(
                        domain="product",
                        fabric_type=product.get("fabric_name"),
                    ),
                    source_document=doc.source,
                )
                chunks.append(chunk)
                summary.ingested += 1
                continue

            if not self._validate_product(product, doc_index):
                summary.skipped += 1
                continue

            product_id: str = product.get("product_id") or product.get("sku", "")
            chunk = Chunk(
                chunk_id=product_id,
                text=doc.content,
                metadata=ChunkMetadata(
                    domain="product",
                    product_id=product_id,
                    category=product.get("category"),
                    fabric_type=product.get("fabric_type") or product.get("fabric"),
                ),
                source_document=doc.source,
            )
            chunks.append(chunk)
            summary.ingested += 1

        logger.info(
            "ProductChunker: ingested=%d, skipped=%d, total=%d",
            summary.ingested,
            summary.skipped,
            summary.total_records,
        )
        return chunks, summary

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_product(self, product: dict[str, Any], record_index: int) -> bool:
        """Return ``True`` if *product* contains all required fields.

        Logs a structured warning for each missing or empty required
        field, including the field name and the record index.  Checks
        known aliases (e.g. ``sku`` for ``product_id``) before flagging.
        """
        valid = True
        for field_name in self.REQUIRED_FIELDS:
            value = product.get(field_name)
            # Check alias if the canonical field is missing
            if not value and field_name in self.FIELD_ALIASES:
                value = product.get(self.FIELD_ALIASES[field_name])
            if not value:  # missing key or empty/None value
                logger.warning(
                    '{"level": "warning", "stage": "product_chunker", '
                    '"missing_field": "%s", "record_index": %d}',
                    field_name,
                    record_index,
                )
                valid = False
        return valid


# ---------------------------------------------------------------------------
# Policy chunker
# ---------------------------------------------------------------------------

# Regex patterns for section boundary detection
_HEADING_RE = re.compile(r"^(#{1,6})\s+", re.MULTILINE)
_HORIZONTAL_RULE_RE = re.compile(r"^(-{3,}|_{3,}|\*{3,})\s*$", re.MULTILINE)

# Patterns that indicate conditional logic blocks
_CONDITIONAL_STARTS = re.compile(
    r"(?:^|\n)\s*[-*]\s*\*?\*?if\b", re.IGNORECASE
)
_CONDITIONAL_KEYWORDS = re.compile(
    r"\b(if|then|else|otherwise|unless|except|provided that|"
    r"in the case|when|where applicable|subject to|eligible|"
    r"not eligible|ineligible|must be|must not)\b",
    re.IGNORECASE,
)


class PolicyChunker:
    """Semantic section-based chunker for policy markdown documents.

    Splits at heading boundaries while ensuring that conditional logic
    blocks (if/then/else rules) are never split across chunks.
    """

    @staticmethod
    def _detect_policy_tags(text: str) -> list[str]:
        """Detect policy topic tags from chunk text content."""
        tags = []
        text_lower = text.lower()
        tag_signals = {
            "return_window": ["30 days", "return window", "within 30", "return period"],
            "final_sale": ["final sale", "non-returnable", "30% or more", "ineligible for return"],
            "community_discount": ["military", "healthcare", "student", "first responder", "community discount"],
            "sale_restriction": ["cannot be redeemed during", "sale period", "promotional event", "cannot be combined"],
            "loyalty_points": ["points", "loyalty", "tier", "a-list", "all access", "vip"],
            "promo_stacking": ["stacking", "cannot be combined", "one discount", "choose one"],
            "shipping_sla": ["shipping", "delivery", "business days", "processing time"],
        }
        for tag, signals in tag_signals.items():
            if any(sig in text_lower for sig in signals):
                tags.append(tag)
        return tags

    def chunk(self, documents: list[RawDocument]) -> list[Chunk]:
        """Chunk a list of policy :class:`RawDocument` instances.

        Returns a flat list of :class:`Chunk` objects with policy
        metadata attached.  Chunk IDs follow the pattern
        ``{policy_type}-section-{n}`` (1-indexed) for deterministic,
        predictable IDs that can be referenced in test queries.
        """
        chunks: list[Chunk] = []

        for doc in documents:
            policy_type: str = doc.metadata.get("policy_type", "unknown")
            effective_date: str | None = doc.metadata.get("effective_date")

            sections = self._split_into_sections(doc.content)

            section_counter = 0
            for section_text in sections:
                stripped = section_text.strip()
                # Skip empty sections and bare horizontal rules
                if not stripped or stripped in ("---", "___", "***"):
                    continue

                tags = self._detect_policy_tags(stripped)
                if tags:
                    stripped = stripped + f"\n\n[Policy tags: {', '.join(tags)}]"

                section_counter += 1
                chunk = Chunk(
                    chunk_id=f"{policy_type}-section-{section_counter}",
                    text=stripped,
                    metadata=ChunkMetadata(
                        domain="policy",
                        policy_type=policy_type,
                        effective_date=effective_date,
                    ),
                    source_document=doc.source,
                )
                chunks.append(chunk)

        logger.info("PolicyChunker: produced %d chunks", len(chunks))
        return chunks

    # ------------------------------------------------------------------
    # Section splitting
    # ------------------------------------------------------------------

    def _split_into_sections(self, text: str) -> list[str]:
        """Split *text* at semantic section boundaries.

        Boundaries are detected via :meth:`_detect_section_boundaries`.
        Adjacent sections are then merged when splitting would break a
        conditional logic block.
        """
        boundaries = self._detect_section_boundaries(text)

        if not boundaries:
            return [text] if text.strip() else []

        sections: list[str] = []
        for start, end in boundaries:
            sections.append(text[start:end])

        # Merge sections that would split conditional logic
        merged = self._merge_conditional_sections(sections)
        return merged

    def _detect_section_boundaries(self, text: str) -> list[tuple[int, int]]:
        """Identify heading-based and horizontal-rule section boundaries.

        Returns a list of ``(start, end)`` character offset pairs, one
        per detected section.  Sections are defined by markdown headings
        (``# …``) and horizontal rules (``---``, ``___``, ``***``).
        """
        # Collect all boundary positions (line starts)
        boundary_positions: list[int] = [0]  # always start at the beginning

        for match in _HEADING_RE.finditer(text):
            pos = match.start()
            if pos not in boundary_positions:
                boundary_positions.append(pos)

        for match in _HORIZONTAL_RULE_RE.finditer(text):
            pos = match.start()
            if pos not in boundary_positions:
                boundary_positions.append(pos)

        boundary_positions.sort()

        # Convert positions to (start, end) ranges
        ranges: list[tuple[int, int]] = []
        for i, start in enumerate(boundary_positions):
            end = boundary_positions[i + 1] if i + 1 < len(boundary_positions) else len(text)
            ranges.append((start, end))

        return ranges

    # ------------------------------------------------------------------
    # Conditional logic preservation
    # ------------------------------------------------------------------

    def _merge_conditional_sections(self, sections: list[str]) -> list[str]:
        """Merge adjacent sections when splitting would break a conditional block.

        If a section ends mid-conditional (has an opening ``if`` without
        a matching resolution) and the next section continues the
        conditional, the two are merged.
        """
        if not sections:
            return sections

        merged: list[str] = [sections[0]]

        for section in sections[1:]:
            prev = merged[-1]
            # If the previous section has an incomplete conditional and
            # the current section continues it, merge them.
            if (
                self._has_open_conditional(prev)
                and self._continues_conditional(section)
            ):
                merged[-1] = prev.rstrip() + "\n\n" + section.lstrip()
            else:
                merged.append(section)

        return merged

    @staticmethod
    def _has_open_conditional(text: str) -> bool:
        """Return ``True`` if *text* contains a conditional that isn't resolved."""
        has_if = bool(re.search(r"\bif\b", text, re.IGNORECASE))
        has_resolution = bool(
            re.search(r"\b(then|else|otherwise)\b", text, re.IGNORECASE)
        )
        # Open conditional: has an "if" but no resolution keyword
        return has_if and not has_resolution

    @staticmethod
    def _continues_conditional(text: str) -> bool:
        """Return ``True`` if *text* starts with or contains conditional continuation."""
        # Check if the section begins with a continuation keyword
        first_line = text.strip().split("\n", 1)[0].lower()
        continuation_words = ("then", "else", "otherwise", "except", "unless")
        for word in continuation_words:
            if word in first_line:
                return True
        return False

    def _contains_complete_conditionals(self, text: str) -> bool:
        """Return ``True`` if all conditional blocks in *text* are complete.

        A conditional block is considered complete when every ``if``
        clause has a corresponding resolution (``then``, ``else``,
        ``otherwise``) within the same text span.
        """
        if_count = len(re.findall(r"\bif\b", text, re.IGNORECASE))
        if if_count == 0:
            return True  # no conditionals to worry about

        resolution_count = len(
            re.findall(
                r"\b(then|else|otherwise)\b", text, re.IGNORECASE
            )
        )
        return resolution_count >= if_count
