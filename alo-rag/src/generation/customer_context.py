"""Customer context injector for the ALO RAG generation engine.

Retrieves customer order data via structured JSON lookup by ``customer_id``
rather than embedding similarity search.  This design avoids privacy risks
from embedding personal data and ensures precise, up-to-date results for
customer queries.

Requirements: 4.1, 4.2, 4.3
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.models import CustomerProfile, Order, OrderItem

logger = logging.getLogger(__name__)


class CustomerContextInjector:
    """Retrieves customer data via structured lookup (not embedding search).

    Customer profiles are loaded once from a JSON file and indexed by
    ``customer_id`` for O(1) lookups.

    Parameters
    ----------
    data_path:
        Path to the ``customers.json`` file containing the customer data.
    """

    def __init__(self, data_path: Path) -> None:
        self.data_path = Path(data_path)
        self._profiles: dict[str, CustomerProfile] = {}
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_customer(self, customer_id: str) -> CustomerProfile | None:
        """Return the :class:`CustomerProfile` for *customer_id*, or ``None``.

        Parameters
        ----------
        customer_id:
            The unique customer identifier (e.g. ``"CUST-001"``).

        Returns
        -------
        CustomerProfile | None
            The full customer profile including order history, or ``None``
            if the customer ID does not exist in the data source.
        """
        profile = self._profiles.get(customer_id)
        if profile is None:
            logger.debug(
                "CustomerContextInjector: customer_id=%r not found",
                customer_id,
            )
        return profile

    def list_customers(self) -> list[str]:
        """Return a sorted list of all available customer IDs.

        Returns
        -------
        list[str]
            Customer IDs present in the loaded data source.
        """
        return sorted(self._profiles.keys())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load and index customer profiles from the JSON data file."""
        if not self.data_path.exists():
            logger.warning(
                "Customer data file not found: %s — no profiles loaded",
                self.data_path,
            )
            return

        try:
            raw = json.loads(self.data_path.read_text(encoding="utf-8"))
            customers_raw: list[dict[str, Any]] = raw.get("customers", [])

            for entry in customers_raw:
                profile = self._parse_profile(entry)
                self._profiles[profile.customer_id] = profile

            logger.info(
                "CustomerContextInjector: loaded %d customer profiles from %s",
                len(self._profiles),
                self.data_path,
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            logger.exception(
                "Failed to parse customer data from %s",
                self.data_path,
            )

    @staticmethod
    def _parse_profile(data: dict[str, Any]) -> CustomerProfile:
        """Parse a single customer profile dict into a :class:`CustomerProfile`."""
        orders: list[Order] = []
        for order_data in data.get("orders", []):
            items: list[OrderItem] = []
            for item_data in order_data.get("items", []):
                items.append(
                    OrderItem(
                        product_id=item_data.get("sku", item_data.get("product_id", "")),
                        product_name=item_data.get("name", item_data.get("product_name", "")),
                        quantity=item_data.get("quantity", 1),
                        price=float(item_data.get("unit_price", item_data.get("price", 0.0))),
                        size=item_data.get("size", ""),
                        was_discounted=item_data.get("was_discounted", False),
                        discount_pct=int(item_data.get("discount_pct", 0)),
                        final_sale=item_data.get("final_sale", False),
                    )
                )
            orders.append(
                Order(
                    order_id=order_data["order_id"],
                    date=order_data.get("order_date", order_data.get("date", "")),
                    items=items,
                    status=order_data.get("order_status", order_data.get("status", "unknown")),
                    total=float(order_data.get("total", 0.0)),
                )
            )

        return CustomerProfile(
            customer_id=data["customer_id"],
            name=data.get("name", ""),
            email=data.get("email", ""),
            orders=orders,
            loyalty_tier=data.get("loyalty_tier", ""),
        )
