# Natural Language to GraphQL Enterprise Solution

## Overview
An enterprise-level agentic system that converts natural language queries to GraphQL for a luxury watch retail company. The system retrieves data from a relational database and presents results with intelligent visualizations.

## Features
- **Complex Relational Database**: Mock enterprise data for watches, customers, orders, inventory, suppliers
- **GraphQL Layer**: Type-safe API wrapper over the database
- **AI Agent**: LangChain-based agent that converts NL to GraphQL
- **Smart Visualizations**: Context-aware chart generation (bar, line, pie, scatter, histogram)
- **Interactive Mode**: Ask questions in natural language and get instant answers
- **Enterprise Complexity**: Realistic data with 8 brands, 24 watch models, 200 customers, 500+ orders

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                   (Natural Language Query)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AGENT LAYER                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  NL to GraphQL Agent (LangChain + GPT-4/Claude)          │  │
│  │  • Understands natural language                          │  │
│  │  • Generates GraphQL queries                             │  │
│  │  • Decides visualization type                            │  │
│  │  • Generates natural language answers                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      GRAPHQL LAYER                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Strawberry GraphQL Schema                               │  │
│  │  • Type-safe API                                         │  │
│  │  • Complex queries with filters                          │  │
│  │  • Nested relationships                                  │  │
│  │  • Aggregation queries                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE LAYER                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  SQLAlchemy ORM + SQLite                                 │  │
│  │  • Brands, Categories, Watches                           │  │
│  │  • Customers, Orders, OrderItems                         │  │
│  │  • Inventory, Suppliers                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   VISUALIZATION LAYER                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Plotly Interactive Charts                               │  │
│  │  • Bar, Line, Pie, Scatter, Histogram                    │  │
│  │  • Context-aware chart selection                         │  │
│  │  • HTML export for viewing                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack
1. **Database Layer**: SQLite with SQLAlchemy ORM
2. **GraphQL Layer**: Strawberry GraphQL
3. **Agent Layer**: LangChain with OpenAI/Anthropic
4. **Visualization Layer**: Plotly for interactive charts
5. **Data Generation**: Faker for realistic mock data

## Quick Start

### Prerequisites
- Python 3.10+
- OpenAI API key or Anthropic API key

### Installation

1. **Install dependencies** (from repository root)
```bash
pip install -r requirements.txt
```

2. **Configure environment** (edit `.env` in repository root)
```bash
# Ensure these variables are set in your root .env file:
OPENAI_API_KEY=your_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
DATABASE_URL=sqlite:///./nl-to-graphql-enterprise-solution/watches_enterprise.db
```

3. **Test setup**
```bash
cd nl-to-graphql-enterprise-solution
python test_setup.py
```

4. **Run the application**
```bash
# Interactive mode
python main.py

# Demo mode
python main.py demo

# Initialize/reset database
python main.py init
```

## Usage Examples

### Interactive Mode
```bash
$ python main.py

💎 Welcome to the Watch Retail Intelligence System
================================================================================
Ask questions about watches, customers, orders, inventory, and sales!
Type 'exit' or 'quit' to end the session.
================================================================================

🔮 Your question: Show me the top 5 best-selling watch models

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

1. Rolex Submariner - 45 units sold, $1,350,000 in revenue
2. Omega Speedmaster - 42 units sold, $840,000 in revenue
3. TAG Heuer Carrera - 38 units sold, $456,000 in revenue
...
================================================================================

📊 Generating bar chart...
📁 Chart saved to: chart_bar.html
   Open 'chart_bar.html' in your browser to view the interactive chart.
```

### Example Queries

**Sales & Revenue Analysis**
- "Show me the top 10 best-selling watch models"
- "What's the revenue trend over the last 6 months?"
- "Which watch brand generates the most revenue?"

**Customer Insights**
- "List all VIP customers"
- "Which customers have spent more than $50,000?"
- "Show me customers from the USA"

**Inventory Management**
- "Show current inventory levels for all watches"
- "Which watches are low on stock?"
- "What watches need to be reordered?"

**Product Information**
- "Show me all luxury watches priced above $30,000"
- "List all diving watches"
- "What limited edition watches are available?"

## Project Structure
- `database/` - Database models, connection, and seed data
- `graphql_layer/` - GraphQL schema and resolvers
- `agent/` - NL to GraphQL conversion agent
- `visualization/` - Chart generation logic
- `main.py` - Main application entry point
- Configuration uses root-level `requirements.txt` and `.env`

## Documentation
- **[GET_STARTED.md](GET_STARTED.md)** - 5-minute quick start guide
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command reference
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup instructions
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Technical architecture
- **[WORKFLOW.md](WORKFLOW.md)** - System workflow diagrams
- **[INDEX.md](INDEX.md)** - Complete documentation index
- **[sample_queries.txt](sample_queries.txt)** - 50+ example queries
