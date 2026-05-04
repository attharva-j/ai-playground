from __future__ import annotations

import json
from pathlib import Path


CUSTOMERS_PATH = Path("data/customers/customer_order_history.json")


NEW_CUSTOMERS = [
    {
        "customer_id": "CUST-10501",
        "name": "Nora Blake",
        "email": "nora.blake@example.com",
        "loyalty_tier": "All Access",
        "loyalty_points": 120,
        "member_since": "2025-01-04",
        "orders": [
            {
                "order_id": "ALO-2025-105001",
                "order_date": "2025-02-14",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "Standard",
                "delivery_address": "Austin, TX",
                "subtotal": 118.00,
                "shipping": 7.95,
                "total": 125.95,
                "payment_method": "Visa ending 1021",
                "notes": "Standard return-eligible order inside normal return window",
                "items": [
                    {
                        "sku": "W5561R-BLK",
                        "name": "High-Waist Airlift Legging",
                        "color": "Black",
                        "size": "M",
                        "quantity": 1,
                        "unit_price": 118.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10502",
        "name": "Marcus Lee",
        "email": "marcus.lee@example.com",
        "loyalty_tier": "A-List",
        "loyalty_points": 760,
        "member_since": "2023-06-18",
        "orders": [
            {
                "order_id": "ALO-2024-105002",
                "order_date": "2024-11-29",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "Free Standard",
                "delivery_address": "Chicago, IL",
                "subtotal": 82.00,
                "shipping": 0.00,
                "total": 57.40,
                "payment_method": "Mastercard ending 2209",
                "notes": "Black Friday discounted final sale item",
                "items": [
                    {
                        "sku": "W2201R-BLK",
                        "name": "Airlift Suit Up Bra",
                        "color": "Black",
                        "size": "L",
                        "quantity": 1,
                        "unit_price": 82.00,
                        "was_discounted": True,
                        "discount_pct": 30,
                        "final_sale": True
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10503",
        "name": "Priya Nair",
        "email": "priya.nair@example.com",
        "loyalty_tier": "VIP",
        "loyalty_points": 1840,
        "member_since": "2021-03-09",
        "orders": [
            {
                "order_id": "ALO-2024-105003",
                "order_date": "2024-08-01",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "Free 2-Day",
                "delivery_address": "Seattle, WA",
                "subtotal": 148.00,
                "shipping": 0.00,
                "total": 148.00,
                "payment_method": "Amex ending 8801",
                "notes": "Delivered order outside the standard return window",
                "items": [
                    {
                        "sku": "W6201R-BNE",
                        "name": "ALO Softsculpt High-Waist Legging",
                        "color": "Bone",
                        "size": "S",
                        "quantity": 1,
                        "unit_price": 148.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10504",
        "name": "Evan Reed",
        "email": "evan.reed@example.com",
        "loyalty_tier": "All Access",
        "loyalty_points": 90,
        "member_since": "2025-02-01",
        "orders": [
            {
                "order_id": "ALO-2025-105004",
                "order_date": "2025-02-20",
                "order_status": "Cancelled",
                "channel": "Online",
                "shipping_method": "Standard",
                "delivery_address": "Denver, CO",
                "subtotal": 98.00,
                "shipping": 7.95,
                "total": 0.00,
                "payment_method": "Visa ending 3310",
                "notes": "Cancelled before fulfillment; no shipment created",
                "items": [
                    {
                        "sku": "M6801R-BLK",
                        "name": "ALO Vapor Crewneck Short Sleeve",
                        "color": "Black",
                        "size": "M",
                        "quantity": 1,
                        "unit_price": 98.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10505",
        "name": "Camila Torres",
        "email": "camila.torres@example.com",
        "loyalty_tier": "A-List",
        "loyalty_points": 640,
        "member_since": "2022-09-12",
        "orders": [
            {
                "order_id": "ALO-2025-105005",
                "order_date": "2025-01-18",
                "order_status": "Return Requested — Pending",
                "channel": "Online",
                "shipping_method": "Standard",
                "delivery_address": "Miami, FL",
                "subtotal": 138.00,
                "shipping": 0.00,
                "total": 138.00,
                "payment_method": "Visa ending 9022",
                "notes": "Return requested within the eligible return window",
                "items": [
                    {
                        "sku": "W5766R-IVY",
                        "name": "High-Waist Airlift Legging",
                        "color": "Ivy",
                        "size": "S",
                        "quantity": 1,
                        "unit_price": 138.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False,
                        "return_status": "Return Requested — Pending",
                        "return_initiated_date": "2025-02-02"
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10506",
        "name": "Julian Brooks",
        "email": "julian.brooks@example.com",
        "loyalty_tier": "All Access",
        "loyalty_points": 220,
        "member_since": "2024-07-27",
        "orders": [
            {
                "order_id": "ALO-2024-105006",
                "order_date": "2024-12-02",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "Standard",
                "delivery_address": "Portland, OR",
                "subtotal": 168.00,
                "shipping": 0.00,
                "total": 134.40,
                "payment_method": "Mastercard ending 4419",
                "notes": "Cyber Monday promotional order; discount stacking should be checked",
                "promo_code": "CYBER20",
                "items": [
                    {
                        "sku": "M3012R-GRY",
                        "name": "Triumph Hoodie",
                        "color": "Athletic Heather Grey",
                        "size": "L",
                        "quantity": 1,
                        "unit_price": 168.00,
                        "was_discounted": True,
                        "discount_pct": 20,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10507",
        "name": "Maya Chen",
        "email": "maya.chen@example.com",
        "loyalty_tier": "VIP",
        "loyalty_points": 2410,
        "member_since": "2020-11-02",
        "orders": [
            {
                "order_id": "ALO-2025-105007",
                "order_date": "2025-02-03",
                "order_status": "Partially Returned",
                "channel": "Online",
                "shipping_method": "Free Express",
                "delivery_address": "San Francisco, CA",
                "subtotal": 230.00,
                "shipping": 0.00,
                "total": 230.00,
                "payment_method": "Amex ending 1114",
                "notes": "Multi-item order with one item returned and one retained",
                "items": [
                    {
                        "sku": "W5561R-ESP",
                        "name": "High-Waist Airlift Legging",
                        "color": "Espresso",
                        "size": "XS",
                        "quantity": 1,
                        "unit_price": 128.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False,
                        "return_status": "Returned — Refund Issued"
                    },
                    {
                        "sku": "W9142R-ESP",
                        "name": "Airlift Intrigue Bra",
                        "color": "Espresso",
                        "size": "XS",
                        "quantity": 1,
                        "unit_price": 102.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False,
                        "return_status": "Kept"
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10508",
        "name": "Owen Miller",
        "email": "owen.miller@example.com",
        "loyalty_tier": "All Access",
        "loyalty_points": 310,
        "member_since": "2024-04-10",
        "orders": [
            {
                "order_id": "ALO-2025-105008",
                "order_date": "2025-01-25",
                "order_status": "Exchange Completed",
                "channel": "Store",
                "shipping_method": "N/A",
                "delivery_address": "In-store purchase — New York, NY",
                "subtotal": 118.00,
                "shipping": 0.00,
                "total": 118.00,
                "payment_method": "Apple Pay",
                "notes": "In-store exchange completed for size change",
                "items": [
                    {
                        "sku": "M7002R-WHT",
                        "name": "Conquer Reform Short Sleeve",
                        "color": "White",
                        "size": "M",
                        "quantity": 1,
                        "unit_price": 118.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False,
                        "exchange_status": "Exchanged from size S to size M"
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10509",
        "name": "Sofia Alvarez",
        "email": "sofia.alvarez@example.com",
        "loyalty_tier": "A-List",
        "loyalty_points": 980,
        "member_since": "2022-01-22",
        "orders": [
            {
                "order_id": "ALO-2025-105009",
                "order_date": "2025-02-22",
                "order_status": "Split Shipment",
                "channel": "Online",
                "shipping_method": "Standard",
                "delivery_address": "Phoenix, AZ",
                "subtotal": 246.00,
                "shipping": 0.00,
                "total": 246.00,
                "payment_method": "Visa ending 7820",
                "notes": "Split shipment: one item delivered, one item still in transit",
                "items": [
                    {
                        "sku": "W5561R-BLK",
                        "name": "High-Waist Airlift Legging",
                        "color": "Black",
                        "size": "M",
                        "quantity": 1,
                        "unit_price": 128.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False,
                        "shipment_status": "Delivered"
                    },
                    {
                        "sku": "W9142R-WHT",
                        "name": "Airlift Intrigue Bra",
                        "color": "White",
                        "size": "M",
                        "quantity": 1,
                        "unit_price": 118.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False,
                        "shipment_status": "In Transit"
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10510",
        "name": "Liam Carter",
        "email": "liam.carter@example.com",
        "loyalty_tier": "All Access",
        "loyalty_points": 45,
        "member_since": "2025-02-09",
        "orders": [
            {
                "order_id": "ALO-2025-105010",
                "order_date": "2025-02-28",
                "order_status": "Processing",
                "channel": "Online",
                "shipping_method": "Standard",
                "delivery_address": "Nashville, TN",
                "subtotal": 74.00,
                "shipping": 7.95,
                "total": 81.95,
                "payment_method": "Mastercard ending 6721",
                "notes": "New order still processing; no tracking number yet",
                "items": [
                    {
                        "sku": "A1001R-BLK",
                        "name": "Performance No-Show Sock 3-Pack",
                        "color": "Black",
                        "size": "One Size",
                        "quantity": 1,
                        "unit_price": 74.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10511",
        "name": "Grace Kim",
        "email": "grace.kim@example.com",
        "loyalty_tier": "VIP",
        "loyalty_points": 3120,
        "member_since": "2019-08-15",
        "orders": [
            {
                "order_id": "ALO-2024-105011",
                "order_date": "2024-12-26",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "International Standard",
                "delivery_address": "Toronto, ON, Canada",
                "subtotal": 198.00,
                "shipping": 24.95,
                "total": 222.95,
                "payment_method": "Visa ending 5567",
                "notes": "International order; return and shipping rules may differ",
                "items": [
                    {
                        "sku": "W8204R-IVR",
                        "name": "Alosoft Courtside Tennis Dress",
                        "color": "Ivory",
                        "size": "S",
                        "quantity": 1,
                        "unit_price": 198.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10512",
        "name": "Dylan Foster",
        "email": "dylan.foster@example.com",
        "loyalty_tier": "A-List",
        "loyalty_points": 0,
        "expired_loyalty_points": 420,
        "member_since": "2022-05-07",
        "orders": [
            {
                "order_id": "ALO-2024-105012",
                "order_date": "2024-10-10",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "Standard",
                "delivery_address": "Charlotte, NC",
                "subtotal": 128.00,
                "shipping": 0.00,
                "total": 128.00,
                "payment_method": "Visa ending 9004",
                "notes": "Customer has expired loyalty points",
                "items": [
                    {
                        "sku": "M9001R-NVY",
                        "name": "Conquer Performance Tank",
                        "color": "Navy",
                        "size": "L",
                        "quantity": 1,
                        "unit_price": 128.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10513",
        "name": "Hannah Wright",
        "email": "hannah.wright@example.com",
        "loyalty_tier": "All Access",
        "loyalty_points": 185,
        "member_since": "2024-12-19",
        "orders": [
            {
                "order_id": "ALO-2025-105013",
                "order_date": "2025-01-05",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "Standard",
                "delivery_address": "Raleigh, NC",
                "subtotal": 136.00,
                "shipping": 7.95,
                "total": 122.35,
                "payment_method": "Discover ending 3380",
                "notes": "Community discount used; validate against promo stacking restrictions",
                "promo_code": "COMMUNITY10",
                "discount_type": "Community Discount",
                "items": [
                    {
                        "sku": "W9142R-BLK",
                        "name": "Airlift Intrigue Bra",
                        "color": "Black",
                        "size": "M",
                        "quantity": 1,
                        "unit_price": 136.00,
                        "was_discounted": True,
                        "discount_pct": 10,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10514",
        "name": "Noah Patel",
        "email": "noah.patel@example.com",
        "loyalty_tier": "VIP",
        "loyalty_points": 2760,
        "member_since": "2020-04-30",
        "orders": [
            {
                "order_id": "ALO-2024-105014",
                "order_date": "2024-09-15",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "Free Express",
                "delivery_address": "Boston, MA",
                "subtotal": 394.00,
                "shipping": 0.00,
                "total": 394.00,
                "payment_method": "Amex ending 6640",
                "notes": "Multiple seasonal purchases for purchase-history questions",
                "items": [
                    {
                        "sku": "W5561R-ESP",
                        "name": "High-Waist Airlift Legging",
                        "color": "Espresso",
                        "size": "S",
                        "quantity": 1,
                        "unit_price": 128.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    },
                    {
                        "sku": "M3012R-GRY",
                        "name": "Triumph Hoodie",
                        "color": "Athletic Heather Grey",
                        "size": "M",
                        "quantity": 1,
                        "unit_price": 168.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    },
                    {
                        "sku": "M6801R-BLK",
                        "name": "ALO Vapor Crewneck Short Sleeve",
                        "color": "Black",
                        "size": "M",
                        "quantity": 1,
                        "unit_price": 98.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    }
                ]
            },
            {
                "order_id": "ALO-2025-105014",
                "order_date": "2025-02-10",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "Free Express",
                "delivery_address": "Boston, MA",
                "subtotal": 198.00,
                "shipping": 0.00,
                "total": 198.00,
                "payment_method": "Amex ending 6640",
                "notes": "Recent winter-season purchase",
                "items": [
                    {
                        "sku": "W8204R-IVR",
                        "name": "Alosoft Courtside Tennis Dress",
                        "color": "Ivory",
                        "size": "S",
                        "quantity": 1,
                        "unit_price": 198.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10515",
        "name": "Isabella Rossi",
        "email": "isabella.rossi@example.com",
        "loyalty_tier": "A-List",
        "loyalty_points": 890,
        "member_since": "2021-12-03",
        "orders": [
            {
                "order_id": "ALO-2025-105015",
                "order_date": "2025-02-01",
                "order_status": "Delivered — Issue Reported",
                "channel": "Online",
                "shipping_method": "Standard",
                "delivery_address": "Las Vegas, NV",
                "subtotal": 128.00,
                "shipping": 0.00,
                "total": 128.00,
                "payment_method": "Visa ending 4507",
                "notes": "Customer reported package marked delivered but not received",
                "issue_status": "Delivery investigation opened",
                "items": [
                    {
                        "sku": "W5561R-WHT",
                        "name": "High-Waist Airlift Legging",
                        "color": "White",
                        "size": "M",
                        "quantity": 1,
                        "unit_price": 128.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10516",
        "name": "Theo Martin",
        "email": "theo.martin@example.com",
        "loyalty_tier": "All Access",
        "loyalty_points": 275,
        "member_since": "2024-03-22",
        "orders": [
            {
                "order_id": "ALO-2024-105016",
                "order_date": "2024-12-01",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "Standard",
                "delivery_address": "Atlanta, GA",
                "subtotal": 276.00,
                "shipping": 0.00,
                "total": 207.00,
                "payment_method": "Mastercard ending 1299",
                "notes": "Cyber Monday order with multiple discounted items",
                "promo_code": "CYBER25",
                "items": [
                    {
                        "sku": "W2201R-BLK",
                        "name": "Airlift Suit Up Bra",
                        "color": "Black",
                        "size": "S",
                        "quantity": 1,
                        "unit_price": 92.00,
                        "was_discounted": True,
                        "discount_pct": 25,
                        "final_sale": True
                    },
                    {
                        "sku": "W5561R-BLK",
                        "name": "High-Waist Airlift Legging",
                        "color": "Black",
                        "size": "S",
                        "quantity": 1,
                        "unit_price": 184.00,
                        "was_discounted": True,
                        "discount_pct": 25,
                        "final_sale": True
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10517",
        "name": "Zoe Bennett",
        "email": "zoe.bennett@example.com",
        "loyalty_tier": "VIP",
        "loyalty_points": 1990,
        "member_since": "2021-06-11",
        "orders": [
            {
                "order_id": "ALO-2025-105017",
                "order_date": "2025-02-12",
                "order_status": "Refund Issued",
                "channel": "Online",
                "shipping_method": "Free Standard",
                "delivery_address": "San Diego, CA",
                "subtotal": 150.00,
                "shipping": 0.00,
                "total": 150.00,
                "payment_method": "Gift Card",
                "notes": "Gift card purchase refunded back to original gift card",
                "refund_status": "Refund Issued to Gift Card",
                "items": [
                    {
                        "sku": "W6201R-TRF",
                        "name": "ALO Softsculpt High-Waist Legging",
                        "color": "Truffle",
                        "size": "M",
                        "quantity": 1,
                        "unit_price": 150.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False,
                        "return_status": "Returned — Refund Issued"
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10518",
        "name": "Amara Johnson",
        "email": "amara.johnson@example.com",
        "loyalty_tier": "A-List",
        "loyalty_points": 1125,
        "member_since": "2022-10-01",
        "orders": [
            {
                "order_id": "ALO-2024-105018",
                "order_date": "2024-06-18",
                "order_status": "Delivered",
                "channel": "Store",
                "shipping_method": "N/A",
                "delivery_address": "In-store purchase — Los Angeles, CA",
                "subtotal": 188.00,
                "shipping": 0.00,
                "total": 188.00,
                "payment_method": "Visa ending 7342",
                "notes": "In-store purchase, receipt available, outside return window",
                "items": [
                    {
                        "sku": "W8204R-BLK",
                        "name": "Alosoft Courtside Tennis Dress",
                        "color": "Black",
                        "size": "M",
                        "quantity": 1,
                        "unit_price": 188.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10519",
        "name": "Benjamin Stone",
        "email": "benjamin.stone@example.com",
        "loyalty_tier": "All Access",
        "loyalty_points": 330,
        "member_since": "2024-08-08",
        "orders": [
            {
                "order_id": "ALO-2025-105019",
                "order_date": "2025-01-31",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "Expedited",
                "delivery_address": "Minneapolis, MN",
                "subtotal": 128.00,
                "shipping": 14.95,
                "total": 142.95,
                "payment_method": "PayPal",
                "notes": "Expedited shipping paid; useful for shipping SLA/refund questions",
                "items": [
                    {
                        "sku": "M9001R-BLK",
                        "name": "Conquer Performance Tank",
                        "color": "Black",
                        "size": "XL",
                        "quantity": 1,
                        "unit_price": 128.00,
                        "was_discounted": False,
                        "discount_pct": 0,
                        "final_sale": False
                    }
                ]
            }
        ]
    },
    {
        "customer_id": "CUST-10520",
        "name": "Elena Garcia",
        "email": "elena.garcia@example.com",
        "loyalty_tier": "VIP",
        "loyalty_points": 3580,
        "member_since": "2018-05-26",
        "orders": [
            {
                "order_id": "ALO-2025-105020",
                "order_date": "2025-02-17",
                "order_status": "Delivered",
                "channel": "Online",
                "shipping_method": "Free Express",
                "delivery_address": "Dallas, TX",
                "subtotal": 300.00,
                "shipping": 0.00,
                "total": 255.00,
                "payment_method": "Amex ending 7188",
                "notes": "Aloversary promotional purchase by VIP customer",
                "promo_code": "ALOVERSARY15",
                "items": [
                    {
                        "sku": "W5561R-ALM",
                        "name": "High-Waist Airlift Legging",
                        "color": "Almond",
                        "size": "S",
                        "quantity": 1,
                        "unit_price": 128.00,
                        "was_discounted": True,
                        "discount_pct": 15,
                        "final_sale": False
                    },
                    {
                        "sku": "W9142R-ALM",
                        "name": "Airlift Intrigue Bra",
                        "color": "Almond",
                        "size": "S",
                        "quantity": 1,
                        "unit_price": 102.00,
                        "was_discounted": True,
                        "discount_pct": 15,
                        "final_sale": False
                    },
                    {
                        "sku": "A1001R-WHT",
                        "name": "Performance No-Show Sock 3-Pack",
                        "color": "White",
                        "size": "One Size",
                        "quantity": 1,
                        "unit_price": 70.00,
                        "was_discounted": True,
                        "discount_pct": 15,
                        "final_sale": False
                    }
                ]
            }
        ]
    }
]

def main() -> None:
    data = json.loads(CUSTOMERS_PATH.read_text(encoding="utf-8"))
    customers = data.setdefault("customers", [])

    existing_ids = {c["customer_id"] for c in customers}

    generated = []
    base_templates = NEW_CUSTOMERS

    next_num = 10505
    while len(customers) + len(generated) < 25:
        template = base_templates[(next_num - 10505) % len(base_templates)]
        customer = json.loads(json.dumps(template))
        customer["customer_id"] = f"CUST-{next_num}"
        customer["name"] = f"Synthetic Customer {next_num}"
        customer["email"] = f"synthetic.customer.{next_num}@example.com"
        customer["orders"][0]["order_id"] = f"ALO-2025-{next_num}"
        customer["orders"][0]["notes"] = (
            customer["orders"][0].get("notes", "") + " — generated edge-case profile"
        )

        if customer["customer_id"] not in existing_ids:
            generated.append(customer)

        next_num += 1

    customers.extend(generated)
    CUSTOMERS_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Added {len(generated)} customers. Total={len(customers)}")


if __name__ == "__main__":
    main()