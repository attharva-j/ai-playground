# ALO Senior AI Engineer — Case Study Data Package

**Version:** 2025-Q1  
**Companion to:** ALO Senior AI Engineer Interview Case Brief (RAG Architecture, Retrieval & Evaluation)

---

## Overview

This data package provides the source materials for the three knowledge domains described in the case brief. All data is grounded in publicly available information from aloyoga.com and reflects real products, policies, and program structures as of early 2025. Customer data is entirely synthetic — names, emails, and order IDs are fictional.

---

## Package Contents

```
alo_data_package/
├── README.md                          ← This file
├── products/
│   └── alo_product_catalog.json       ← Domain 1: Product Knowledge
├── policies/
│   ├── returns_and_exchanges_policy.md  ← Domain 2: Policy (Returns)
│   ├── shipping_policy.md               ← Domain 2: Policy (Shipping)
│   └── alo_access_loyalty_program.md   ← Domain 2: Policy (Loyalty)
└── customers/
    └── customer_order_history.json    ← Domain 3: Customer Context
```

---

## Domain 1 — Product Knowledge (`products/`)

### `alo_product_catalog.json`

A structured JSON catalog of 22 real Alo Yoga SKUs across:
- Women's leggings (full-length, 7/8, flare, ribbed styles)
- Women's sports bras
- Men's shorts, pants, and tops
- Accessories (mats, water bottle)

**Each product record includes:**
- SKU, name, gender, category, subcategory
- Fabric type (with full fabric glossary at the top of the file)
- Price, available sizes, available colors
- Fit notes, inseam measurements, rise type
- Key features, best-use cases, care instructions
- Restocking frequency, bestseller flag, final sale eligibility
- Tags for filtering

**Suggested exercises this enables:**
- "What fabric is the 7/8 Airlift Legging made of?"
- "What's the difference between Airlift and Airbrush?"
- "I'm looking for a compression legging for hot yoga — what do you recommend?"
- "Which leggings have no side seams?"
- "What sizes does the Warrior Mat come in?"
- "What are the care instructions for the Alosoft Lounge Legging?"

---

## Domain 2 — Policy & Operations Intelligence (`policies/`)

Three policy documents in Markdown format, reflecting real Alo Yoga policies grounded in publicly available information.

### `returns_and_exchanges_policy.md`

Covers:
- 30-day return window and conditions
- Final Sale rules (30% discount threshold, specific excluded categories)
- How to initiate an online return via the Returns Portal
- In-store return rules (same-store only, cash transactions)
- Refund processing timeline (2–4 business days)
- Instant Exchange option (credit hold mechanism, 21-day ship-back requirement)
- International return rules (no prepaid labels, customer bears cost)
- Defective item process
- Order cancellation window (1 hour)

**Suggested retrieval challenges this enables:**
- "Can I return the leggings I bought during Black Friday?"
- "How long does it take to get my refund after I drop off the return?"
- "I bought something in-store — can I return it online?"
- "Can I exchange my leggings for a different size directly?"
- "I'm in the UK — how do I return my order?"

### `shipping_policy.md`

Covers:
- Processing times (1–2 business days, extended during peak periods)
- U.S. shipping options: Free Standard, $15 Two-Day, $25 Overnight
- Same-day delivery in select markets
- A-List and All Access member free 2-day shipping perk
- International shipping thresholds ($75 USD free shipping), regional delivery estimates, duties responsibility
- Address accuracy policy
- Lost/damaged package process
- Restock drop schedule (Tuesdays and Thursdays)

### `alo_access_loyalty_program.md`

Covers:
- Three tiers: VIP (1–299 pts), A-List (300–999 pts), All Access (1,000+ pts)
- 1 point per $1 spent (online and in-store, full-price only)
- Tier benefits by level (shipping perks, early access, gifts, events)
- Point redemption rules and restrictions (**cannot redeem during sales**)
- Point expiration (24 months)
- Community discounts (military, healthcare, students, first responders)
- App-exclusive benefits

**Retrieval complexity note:** There is an intentional **policy conflict trap** in this dataset: the loyalty program says members cannot redeem points during sale periods, while casual reading of the returns policy might suggest returns generate "credit." Candidates who build good retrieval should surface both documents when asked about redeeming during a sale.

---

## Domain 3 — Customer Context Queries (`customers/`)

### `customer_order_history.json`

Synthetic order history for 8 customers representing a range of loyalty tiers, purchase behaviors, and edge cases.

| Customer | Tier | Key Scenario |
|----------|------|--------------|
| Maya Patel | A-List | Black Friday Final Sale items — ineligible for return |
| Jordan Kim | All Access | Heavy buyer; Aloversary Final Sale order |
| Sofia Reyes | VIP | New customer; single order, full-price |
| Ethan Brooks | A-List | Pending return within window; re-order required |
| Priya Nair | All Access | Bulk Cyber Monday buyer; all Final Sale |
| Lena Johansson | VIP | **Return rejected** — initiated 34 days post-purchase (outside window) |
| Marcus Webb | A-List | Multi-item order including mat |
| Chloe Zhang | VIP | Brand new customer; order in transit |

**Suggested queries this enables:**
- "Can I return the leggings I bought during Cyber Monday?" (Customer: Priya Nair)
- "What did I order last season?" (Customer: Jordan Kim)
- "I'm trying to return something but the portal rejected me — why?" (Customer: Lena Johansson)
- "What's the status of my current order?" (Customer: Chloe Zhang)
- "I want to exchange my vapor shirt for a larger size — how do I do that?" (Customer: Ethan Brooks)
- "What tier am I in and what are my shipping perks?" (any customer)

---

## Designed Retrieval Challenges

This dataset includes several intentional complexity points to stress-test RAG systems:

1. **Final Sale trap** — Multiple customers have Final Sale items. A naive system might say all items are returnable within 30 days without catching the Final Sale exception.

2. **Cross-domain query** — "Is the item I bought during the Aloversary eligible for return?" requires combining customer order data (Domain 3) + return policy (Domain 2).

3. **Policy nuance** — The return policy and loyalty policy have distinct rules about sale period behavior. A system that chunks these poorly may conflate or miss the restrictions.

4. **Out-of-window rejection** — Lena Johansson's rejected return is explicitly documented. A good system should retrieve this and explain why returns after 30 days are rejected.

5. **No-direct-exchange policy** — Alo does not offer direct exchanges for online orders. Candidates whose systems correctly surface this (and the Instant Exchange workaround) demonstrate strong policy retrieval.

6. **Tier-based shipping benefits** — Shipping entitlements differ by loyalty tier. A query like "do I get free 2-day shipping?" requires cross-referencing customer tier (Domain 3) against loyalty policy (Domain 2).

---

## Data Provenance

| Data Type | Source |
|-----------|--------|
| Product names, SKUs, prices, fabrics | Verified against aloyoga.com product listings |
| Fabric compositions | Sourced from product listings and Alo's published fabric guide |
| Return policy | Verified against aloyoga.com/pages/returns-exchanges |
| Shipping policy | Verified against aloyoga.com/pages/shipping-info |
| Loyalty program | Verified against aloyoga.com/blogs/alo-blog/new-alo-loyalty-program-alo-access and member accounts |
| Customer data | Entirely synthetic — names, emails, and order IDs are fictional |

---

## Usage Notes for Candidates

- You are free to use this data as-is, augment it with additional synthetic records, or restructure it for your ingestion pipeline
- The product catalog JSON is designed to support multiple chunking strategies — per-product, per-fabric type, per-category, etc.
- The policy Markdown files have intentional structural complexity (numbered sections, tables, conditional logic) — your chunking approach should handle these thoughtfully
- The customer order history JSON is structured to require blending retrieved policy knowledge with per-customer context — this is Domain 3's core challenge

---

*All customer data is synthetic. Product and policy data is grounded in publicly available information from aloyoga.com as of early 2025.*
