# Quick Reference Card

## Installation (One-Time Setup)

```bash
# From repository root
pip install -r requirements.txt

# Edit .env in repository root and ensure these are set:
# OPENAI_API_KEY=your_key_here
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4
# DATABASE_URL=sqlite:///./nl-to-graphql-enterprise-solution/watches_enterprise.db

# Test setup
cd nl-to-graphql-enterprise-solution
python test_setup.py
```

## Running the Application

```bash
# Navigate to solution directory
cd nl-to-graphql-enterprise-solution

# Interactive mode (recommended)
python main.py

# Demo mode (5 pre-configured queries)
python main.py demo

# Reset/initialize database
python main.py init
```

## Common Commands

| Command | Description |
|---------|-------------|
| `python main.py` | Start interactive query mode |
| `python main.py demo` | Run demo queries |
| `python main.py init` | Initialize/reset database |
| `python test_setup.py` | Verify installation |

## Sample Queries by Category

### 📊 Sales & Revenue
```
Show me the top 5 best-selling watch models
What's the revenue trend over the last 6 months?
Which watch brand generates the most revenue?
```

### 👥 Customers
```
List all VIP customers
Which customers have spent more than $50,000?
Who are the top 10 customers by lifetime value?
```

### 📦 Inventory
```
Show current inventory levels for all watches
Which watches are low on stock?
What watches need to be reordered?
```

### ⌚ Products
```
Show me all luxury watches priced above $30,000
List all diving watches
What limited edition watches are available?
```

## Chart Types Generated

| Query Type | Chart Type | Example |
|------------|------------|---------|
| Top N items | Bar Chart | "Top 5 selling watches" |
| Trends over time | Line Chart | "Revenue by month" |
| Proportions | Pie Chart | "Sales by category" |
| Comparisons | Bar Chart | "Average price by brand" |
| Distributions | Histogram | "Price distribution" |
| Detailed data | Table | "List all customers" |

## File Outputs

- `chart_bar.html` - Bar charts
- `chart_line.html` - Line charts  
- `chart_pie.html` - Pie charts
- `demo_chart_*.html` - Demo visualizations
- `watches_enterprise.db` - SQLite database

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No module named X" | Run `pip install -r requirements.txt` from repo root |
| "API key not found" | Add key to `.env` file in repo root |
| "Database not found" | Run `python main.py init` from solution directory |
| Charts not showing | Open `.html` files in browser |
| Config not loading | Ensure `.env` is in repository root |

## Project Structure

```
repository-root/
├── requirements.txt       # Dependencies (shared)
├── .env                   # Your API keys (shared)
│
└── nl-to-graphql-enterprise-solution/
    ├── main.py                 # ← Start here
    ├── config.py              # Configuration (loads root .env)
    │
├── database/              # Data layer
│   ├── models.py         # Database schema
│   ├── connection.py     # DB connection
│   └── seed_data.py      # Mock data generator
│
├── graphql_layer/         # API layer
│   └── schema.py         # GraphQL schema
│
├── agent/                 # AI layer
│   ├── nl_to_graphql_agent.py  # Main agent
│   └── prompts.py        # LLM prompts
│
└── visualization/         # Chart layer
    └── chart_generator.py # Plotly charts
```

## Database Schema

**8 Tables:**
- `brands` - Watch manufacturers (Rolex, Omega, etc.)
- `categories` - Watch types (Luxury, Sport, Diving, etc.)
- `watches` - Watch products (24 models)
- `customers` - Buyers (200 customers)
- `orders` - Transactions (500+ orders)
- `order_items` - Line items in orders
- `inventory` - Stock levels
- `suppliers` - Vendors

## GraphQL Queries Available

**Basic Queries:**
- `brands(limit: Int)`
- `categories()`
- `watches(limit, brand_id, category_id, min_price, max_price)`
- `customers(limit, vip_only, min_lifetime_value)`
- `orders(limit, customer_id, status)`
- `inventory(watch_id)`

**Analytics Queries:**
- `topSellingWatches(limit: Int)`
- `revenueByMonth(months: Int)`
- `inventoryStatus(low_stock_only: Boolean)`

## Environment Variables

Add these to `.env` in repository root:

```env
# Required
OPENAI_API_KEY=sk-...          # Get from platform.openai.com
# OR
ANTHROPIC_API_KEY=sk-ant-...   # Get from console.anthropic.com

# Required for this solution
LLM_PROVIDER=openai            # or "anthropic"
LLM_MODEL=gpt-4               # or "gpt-3.5-turbo", "claude-3-sonnet-20240229"
DATABASE_URL=sqlite:///./nl-to-graphql-enterprise-solution/watches_enterprise.db

# Optional
DEBUG=False
```

## Tips for Best Results

1. **Be specific**: "Top 5 selling watches" vs "Show watches"
2. **Use time ranges**: "Last 6 months" vs "Recent"
3. **Specify metrics**: "By revenue" vs "By quantity"
4. **Ask for comparisons**: "Compare X by Y"
5. **Request filters**: "VIP customers only", "Luxury watches above $30k"

## Getting Help

1. **Setup issues**: Check `SETUP_GUIDE.md`
2. **Query examples**: See `sample_queries.txt`
3. **Architecture details**: Read `PROJECT_SUMMARY.md`
4. **Test installation**: Run `python test_setup.py`

## Next Steps

1. ✅ Install dependencies
2. ✅ Configure API key
3. ✅ Test setup
4. ✅ Run demo mode
5. ✅ Try interactive mode
6. ✅ Explore sample queries
7. ✅ View generated charts
8. ✅ Examine GraphQL queries

---

**Need more help?** Check the comprehensive documentation:
- `README.md` - Overview and quick start
- `SETUP_GUIDE.md` - Detailed setup instructions
- `PROJECT_SUMMARY.md` - Architecture and technical details
