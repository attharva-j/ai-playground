# 🚀 Get Started in 5 Minutes

This guide will get you up and running with the Natural Language to GraphQL Enterprise Solution in just 5 minutes.

## Step 1: Install Dependencies (1 minute)

Open your terminal and navigate to the **repository root** (not the solution directory):

```bash
pip install -r requirements.txt
```

You should see packages being installed. Wait for completion.

## Step 2: Configure API Key (1 minute)

Open the `.env` file in the **repository root** and ensure these variables are set:

**For OpenAI:**
```env
OPENAI_API_KEY=sk-your-actual-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
DATABASE_URL=sqlite:///./nl-to-graphql-enterprise-solution/watches_enterprise.db
```

**For Anthropic:**
```env
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-sonnet-20240229
DATABASE_URL=sqlite:///./nl-to-graphql-enterprise-solution/watches_enterprise.db
```

Save the file.

## Step 3: Verify Setup (1 minute)

Navigate to the solution directory and run the setup test:

```bash
cd nl-to-graphql-enterprise-solution
python test_setup.py
```

You should see:
```
✅ PASS: Imports
✅ PASS: Configuration
✅ PASS: Database
✅ PASS: GraphQL
✅ PASS: Agent

🎉 All tests passed! The system is ready to use.
```

If any tests fail, check the error messages and fix the issues.

## Step 4: Run Your First Query (2 minutes)

Start the application:

```bash
python main.py
```

You'll see:
```
💎 Welcome to the Watch Retail Intelligence System
================================================================================
Ask questions about watches, customers, orders, inventory, and sales!
Type 'exit' or 'quit' to end the session.
================================================================================

🔮 Your question:
```

Try this query:
```
Show me the top 5 best-selling watch models
```

The system will:
1. Generate a GraphQL query
2. Execute it against the database
3. Create a visualization
4. Provide a natural language answer

You'll see output like:
```
🔍 Processing query: Show me the top 5 best-selling watch models
📝 Generating GraphQL query...
⚡ Executing GraphQL query...
✅ Query executed successfully!
📊 Determining visualization...
💬 Generating answer...

================================================================================
📋 ANSWER:
================================================================================
Based on the sales data, here are the top 5 best-selling watch models:

1. Rolex Submariner - 45 units sold, generating $1,350,000 in revenue
2. Omega Speedmaster - 42 units sold, generating $840,000 in revenue
3. TAG Heuer Carrera - 38 units sold, generating $456,000 in revenue
4. Breitling Navitimer - 35 units sold, generating $525,000 in revenue
5. Cartier Tank - 33 units sold, generating $495,000 in revenue

The Rolex Submariner is clearly the best performer.
================================================================================

📊 Generating bar chart...
📁 Chart saved to: chart_bar.html
   Open 'chart_bar.html' in your browser to view the interactive chart.
```

## Step 5: View the Visualization

Open `chart_bar.html` in your web browser. You'll see an interactive bar chart showing the top-selling watches.

## What's Next?

### Try More Queries

Here are some queries to try:

**Sales Analysis:**
```
What's the revenue trend over the last 6 months?
Which watch brand generates the most revenue?
```

**Customer Insights:**
```
List all VIP customers
Which customers have spent more than $50,000?
```

**Inventory:**
```
Show current inventory levels for all watches
Which watches are low on stock?
```

**Product Info:**
```
Show me all luxury watches priced above $30,000
List all diving watches
```

### Explore the Documentation

- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick commands and troubleshooting
- **[sample_queries.txt](sample_queries.txt)** - 50+ example queries
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed usage guide
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Technical architecture

### Run Demo Mode

See pre-configured queries in action:

```bash
python main.py demo
```

This runs 5 demo queries and generates visualizations for each.

## Common Issues

### "No module named 'langchain'"
**Solution:** Run `pip install -r requirements.txt`

### "API key not found"
**Solution:** Make sure you created `.env` and added your API key

### "Database not found"
**Solution:** Run `python main.py init` to initialize the database

### Charts not displaying
**Solution:** Make sure you're opening the `.html` files in a web browser

## Tips for Best Results

1. **Be specific**: "Top 5 selling watches" is better than "Show watches"
2. **Use time ranges**: "Last 6 months" is clearer than "Recent"
3. **Specify metrics**: "By revenue" or "By quantity"
4. **Ask for comparisons**: "Compare sales by brand"

## System Overview

```
Your Question
    ↓
AI Agent (converts to GraphQL)
    ↓
GraphQL API (queries database)
    ↓
Database (returns data)
    ↓
AI Agent (decides visualization)
    ↓
Plotly (creates chart)
    ↓
Natural Language Answer + Interactive Chart
```

## Quick Commands Reference

| Command | Purpose |
|---------|---------|
| `python main.py` | Start interactive mode |
| `python main.py demo` | Run demo queries |
| `python main.py init` | Reset database |
| `python test_setup.py` | Verify installation |
| Type `exit` or `quit` | Exit interactive mode |

## Getting Help

1. Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for quick answers
2. Review [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions
3. Try queries from [sample_queries.txt](sample_queries.txt)
4. Read [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for technical details

## Success Checklist

- ✅ Dependencies installed
- ✅ API key configured in `.env`
- ✅ Setup test passed
- ✅ First query executed successfully
- ✅ Chart viewed in browser

Congratulations! You're now ready to explore the full capabilities of the system.

---

**Next Steps:**
- Try queries from [sample_queries.txt](sample_queries.txt)
- Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for more features
- Explore [SETUP_GUIDE.md](SETUP_GUIDE.md) for advanced usage
