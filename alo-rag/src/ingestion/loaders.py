"""Data loaders for the ALO RAG ingestion pipeline.

Provides loaders for the three knowledge domains:
- ProductLoader: parses product catalog JSON into RawDocument list
- PolicyLoader: parses policy markdown files into RawDocument list
- CustomerLoader: parses customer JSON into dict[str, CustomerProfile] for structured lookup
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.models import CustomerProfile, Order, OrderItem, RawDocument

logger = logging.getLogger(__name__)


class ProductLoader:
    """Loads product catalog from a JSON file.

    Expects a JSON file with a top-level ``"products"`` array where each
    element is a product object.  Each product is converted into a
    :class:`RawDocument` with ``domain="product"`` and the full product
    dict stored in ``metadata``.
    """

    def load(self, path: Path) -> list[RawDocument]:
        """Parse *path* and return one :class:`RawDocument` per product."""
        path = Path(path)
        logger.info("Loading product catalog from %s", path)

        with path.open("r", encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)

        # Load fabric glossary for enriching product chunks
        fabric_glossary: dict[str, Any] = data.get("fabric_glossary", {})

        products: list[dict[str, Any]] = data.get("products", [])
        documents: list[RawDocument] = []

        for product in products:
            content = self._product_to_text(product, fabric_glossary)
            doc = RawDocument(
                content=content,
                source=str(path),
                domain="product",
                metadata=product,
            )
            documents.append(doc)

        # Create first-class fabric glossary chunks
        for fabric_name, glossary in fabric_glossary.items():
            fabric_text_parts = [
                f"Fabric: {fabric_name}",
                f"Composition: {glossary.get('composition', 'N/A')}",
                f"Compression Level: {glossary.get('compression_level', 'N/A')}",
                f"Finish: {glossary.get('finish', 'N/A')}",
                f"Description: {glossary.get('description', '')}",
            ]
            key_props = glossary.get("key_properties", [])
            if key_props:
                fabric_text_parts.append(f"Key Properties: {', '.join(key_props)}")
            care = glossary.get("care", "")
            if care:
                fabric_text_parts.append(f"Care: {care}")

            # Find associated product IDs
            associated_products = [
                p.get("sku", p.get("product_id", ""))
                for p in products
                if p.get("fabric", p.get("fabric_type", "")) == fabric_name
            ]
            if associated_products:
                fabric_text_parts.append(f"Products using this fabric: {', '.join(associated_products)}")

            fabric_content = "\n".join(fabric_text_parts)
            fabric_doc = RawDocument(
                content=fabric_content,
                source=str(path),
                domain="product",
                metadata={
                    "entity_type": "fabric",
                    "fabric_name": fabric_name,
                    "chunk_id": f"fabric-{fabric_name.lower().replace(' ', '-')}",
                },
            )
            documents.append(fabric_doc)

        logger.info("Loaded %d product documents (including %d fabric glossary entries) from %s",
                     len(documents), len(fabric_glossary), path)
        return documents

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _product_to_text(product: dict[str, Any], fabric_glossary: dict[str, Any] | None = None) -> str:
        """Concatenate product fields into a single text representation.

        When *fabric_glossary* is provided, the fabric composition and
        properties from the glossary are appended to the product text,
        giving the LLM detailed fabric information for every product.
        """
        parts: list[str] = []

        name = product.get("name", "")
        if name:
            parts.append(f"Product: {name}")

        product_id = product.get("product_id", "") or product.get("sku", "")
        if product_id:
            parts.append(f"Product ID: {product_id}")

        category = product.get("category", "")
        if category:
            parts.append(f"Category: {category}")

        # Handle both "fabric_type" (design doc) and "fabric" (actual data)
        fabric_type = product.get("fabric_type", "") or product.get("fabric", "")
        if fabric_type:
            parts.append(f"Fabric Type: {fabric_type}")

            # Enrich with fabric glossary details
            if fabric_glossary and fabric_type in fabric_glossary:
                glossary = fabric_glossary[fabric_type]
                composition = glossary.get("composition", "")
                if composition:
                    parts.append(f"Fabric Composition: {composition}")
                compression = glossary.get("compression_level", "")
                if compression:
                    parts.append(f"Compression Level: {compression}")
                finish = glossary.get("finish", "")
                if finish:
                    parts.append(f"Finish: {finish}")
                fabric_desc = glossary.get("description", "")
                if fabric_desc:
                    parts.append(f"Fabric Description: {fabric_desc}")
                key_props = glossary.get("key_properties", [])
                if key_props:
                    parts.append(f"Fabric Properties: {', '.join(key_props)}")

        description = product.get("description", "")
        if description:
            parts.append(f"Description: {description}")

        materials = product.get("materials", [])
        if materials:
            parts.append(f"Materials: {', '.join(materials)}")

        # Handle both "sizes" (design doc) and "available_sizes" (actual data)
        sizes = product.get("sizes", []) or product.get("available_sizes", [])
        if sizes:
            parts.append(f"Sizes: {', '.join(sizes)}")

        # Handle both "colors" (design doc) and "available_colors" (actual data)
        colors = product.get("colors", []) or product.get("available_colors", [])
        if colors:
            parts.append(f"Colors: {', '.join(colors)}")

        price = product.get("price") or product.get("price_usd")
        if price is not None:
            parts.append(f"Price: ${float(price):.2f}")

        care = product.get("care_instructions", "")
        if care:
            parts.append(f"Care Instructions: {care}")

        features = product.get("features", [])
        if features:
            parts.append(f"Features: {', '.join(features)}")

        best_for = product.get("best_for", [])
        if best_for:
            parts.append(f"Best For: {', '.join(best_for)}")

        return "\n".join(parts)


class PolicyLoader:
    """Loads policy documents from markdown files.

    Accepts either a single ``.md`` file or a directory containing
    multiple markdown files.  Each file becomes one :class:`RawDocument`
    with ``domain="policy"`` and metadata derived from the filename.
    """

    def load(self, path: Path) -> list[RawDocument]:
        """Parse markdown file(s) at *path* and return :class:`RawDocument` list."""
        path = Path(path)
        logger.info("Loading policy documents from %s", path)

        if path.is_file():
            files = [path]
        elif path.is_dir():
            files = sorted(path.glob("*.md"))
        else:
            logger.warning("Policy path %s does not exist", path)
            return []

        documents: list[RawDocument] = []
        for file_path in files:
            if file_path.name.startswith("."):
                continue
            content = file_path.read_text(encoding="utf-8")
            if not content.strip():
                logger.warning("Skipping empty policy file: %s", file_path)
                continue

            policy_type = self._infer_policy_type(file_path.stem)
            doc = RawDocument(
                content=content,
                source=str(file_path),
                domain="policy",
                metadata={
                    "policy_type": policy_type,
                    "filename": file_path.name,
                },
            )
            documents.append(doc)

        logger.info("Loaded %d policy documents from %s", len(documents), path)
        return documents

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_policy_type(stem: str) -> str:
        """Derive a policy_type label from the filename stem.

        Maps common filename patterns to the canonical policy types used
        throughout the system: ``returns``, ``shipping``, ``promo``, or
        ``loyalty``.
        """
        stem_lower = stem.lower()
        if "return" in stem_lower or "exchange" in stem_lower:
            return "returns"
        if "ship" in stem_lower:
            return "shipping"
        if "promo" in stem_lower:
            return "promo"
        if "loyalty" in stem_lower or "access" in stem_lower:
            return "loyalty"
        return stem_lower


class CustomerLoader:
    """Loads customer order data from a JSON file for structured lookup.

    Returns a ``dict[str, CustomerProfile]`` keyed by ``customer_id``
    so that the :class:`CustomerContextInjector` can perform exact-match
    lookups without embedding personal data.
    """

    def load(self, path: Path) -> dict[str, CustomerProfile]:
        """Parse *path* and return a mapping of customer_id → CustomerProfile."""
        path = Path(path)
        logger.info("Loading customer data from %s", path)

        with path.open("r", encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)

        customers_raw: list[dict[str, Any]] = data.get("customers", [])
        profiles: dict[str, CustomerProfile] = {}

        for cust in customers_raw:
            try:
                profile = self._parse_customer(cust)
                profiles[profile.customer_id] = profile
            except (KeyError, TypeError) as exc:
                logger.warning(
                    "Skipping malformed customer record: %s — %s",
                    cust.get("customer_id", "<unknown>"),
                    exc,
                )

        logger.info("Loaded %d customer profiles from %s", len(profiles), path)
        return profiles

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_customer(data: dict[str, Any]) -> CustomerProfile:
        """Convert a raw JSON dict into a :class:`CustomerProfile`.

        Handles both the design-doc schema (``product_id``, ``date``,
        ``status``) and the actual data-package schema (``sku``,
        ``order_date``, ``order_status``).
        """
        orders: list[Order] = []
        for order_data in data.get("orders", []):
            items: list[OrderItem] = []
            for item_data in order_data.get("items", []):
                items.append(
                    OrderItem(
                        product_id=item_data.get("product_id") or item_data.get("sku", ""),
                        product_name=item_data.get("product_name") or item_data.get("name", ""),
                        quantity=item_data["quantity"],
                        price=item_data.get("price") or item_data.get("unit_price", 0.0),
                        size=item_data["size"],
                        was_discounted=item_data.get("was_discounted", False),
                        discount_pct=item_data.get("discount_pct", 0),
                        final_sale=item_data.get("final_sale", False),
                    )
                )
            orders.append(
                Order(
                    order_id=order_data["order_id"],
                    date=order_data.get("date") or order_data.get("order_date", ""),
                    items=items,
                    status=order_data.get("status") or order_data.get("order_status", ""),
                    total=order_data["total"],
                )
            )

        return CustomerProfile(
            customer_id=data["customer_id"],
            name=data["name"],
            email=data["email"],
            orders=orders,
            loyalty_tier=data.get("loyalty_tier", ""),
        )
