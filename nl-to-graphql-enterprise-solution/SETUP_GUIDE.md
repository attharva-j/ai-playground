# Setup and Usage Guide

## Quick Start

### 1. Install Dependencies

From the repository root:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Edit the `.env` file in the repository root and ensure these variables are set:

```env
# For OpenAI
OPENAI_API_KEY=sk-your-actual-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
DATABASE_URL=sqlite:///./nl-to-graphql-enterprise-solution/watches_enterprise.db

# OR for Anthropic
# ANTHROPIC_API_KEY=your-actual-key-here
# LLM_PROVIDER=anthropic
# LLM_MODEL=claude-3-sonnet-20240229
# DATABASE_URL=sqlite:///./nl-to-graphql-enterprise-solution/watches_enterprise.db
```

### 3. Initialize Database

Navigate to the solution directory and initialize:

```bash
cd nl-to-graphql-enterprise-solution
python main.py init
```

This creates a SQLite database with:
- 8 luxury watch brands (Rolex, Omega, Patek Philippe, etc.)
- 6 watch categories
- 24 watch models with realistic specifications
- 200 customers with purchase history
- 500 orders spanning the last year
- Complete inventory tracking

### 4. Run the Application

#### Interactive Mode (Recommended)

```bash
python main.py
```

This starts an interactive session where you can ask questions in natural language.

#### Demo Mode

```bash
python main.py demo
```

Runs 5 pre-configured demo queries to showcase the system.

## Example Queries

### Sales & Revenue Analysis
- "Show me the top 10 best-selling watch models"
- "What's the revenue trend over the last 6 months?"
- "Which watch brand generates the most revenue?"
- "Show me all orders from the last month"

### Customer Insights
- "List all VIP customers"
- "Which customers have spent more than $50,000?"
- "Show me customers from the USA"
- "Who are the top 5 customers by lifetime value?"

### Inventory Management
- "Show current inventory levels for all watches"
- "Which watches are low on stock?"
- "Show me inventory for Rolex watches"
- "What watches need to be reordered?"

### Product Information
- "Show me all luxury watches priced above $30,000"
- "List all diving watches"
- "Show me watches with automatic movement"
- "What limited edition watches are available?"

### Comparative Analysis
- "Compare sales across different watch categories"
- "Show average price by brand"
- "What's the distribution of watch prices?"

## System Architecture

### 1. Database Layer (`database/`)
- **models.py**: SQLAlchemy ORM models for all entities
- **connection.py**: Database connection management
- **seed_data.py**: Generates realistic mock data using Faker

### 2. GraphQL Layer (`graphql_layer/`)
- **schema.py**: Strawberry GraphQL schema with type definitions and resolvers
- Provides type-safe API over the relational database
- Supports complex queries with nested relationships

### 3. Agent Layer (`agent/`)
- **nl_to_graphql_agent.py**: LangChain-based agent for NL→GraphQL conversion
- **prompts.py**: System prompts and schema documentation
- Uses GPT-4 or Claude for intelligent query generation

### 4. Visualization Layer (`visualization/`)
- **chart_generator.py**: Plotly-based chart generation
- Automatically selects appropriate chart types:
  - **Bar charts**: Category comparisons
  - **Line charts**: Time series and trends
  - **Pie charts**: Proportions and distributions
  - **Scatter plots**: Correlations
  - **Histograms**: Value distributions
  - **Tables**: Detailed data views

## How It Works

1. **User Input**: You ask a question in natural language
2. **Query Generation**: The AI agent converts your question to a GraphQL query
3. **Query Execution**: The GraphQL query is executed against the database
4. **Visualization Decision**: AI determines the best chart type for the data
5. **Answer Generation**: AI creates a natural language response
6. **Chart Creation**: Interactive Plotly chart is generated and saved as HTML

## Output Files

The system generates HTML files for visualizations:
- `chart_bar.html`: Bar charts
- `chart_line.html`: Line charts
- `chart_pie.html`: Pie charts
- `demo_chart_*.html`: Demo query visualizations

Open these files in any web browser to view interactive charts.

## Troubleshooting

### "No module named 'langchain'"
```bash
# From repository root
pip install -r requirements.txt
```

### "API key not found"
Make sure you've added your API key to the `.env` file in the repository root.

### "Database not found"
Run `python main.py init` to initialize the database.

### Charts not displaying
Make sure you have a web browser installed. The charts are saved as HTML files that need to be opened in a browser.

## Advanced Usage

### Custom Queries

You can also use the agent programmatically:

```python
from agent import NLToGraphQLAgent
from visualization import ChartGenerator

agent = NLToGraphQLAgent()
chart_gen = ChartGenerator()

# Process a query
result = agent.process_query("Show me top selling watches")

# Generate visualization
if result["success"]:
    fig = chart_gen.generate_chart(result["data"], result["visualization"])
    chart_gen.save_chart(fig, "my_chart.html")
```

### Direct GraphQL Queries

You can also execute GraphQL queries directly:

```python
from graphql_layer import schema

query = """
query {
  topSellingWatches(limit: 5) {
    model_name
    brand_name
    total_quantity_sold
    total_revenue
  }
}
"""

result = schema.execute_sync(query)
print(result.data)
```

## Database Schema

### Core Tables
- **brands**: Watch manufacturers
- **categories**: Watch categories (Luxury, Sport, Diving, etc.)
- **watches**: Watch products with specifications
- **customers**: Customer information
- **orders**: Customer orders
- **order_items**: Individual items in orders
- **inventory**: Stock levels and warehouse locations
- **suppliers**: Supplier information

### Key Relationships
- Watch → Brand (many-to-one)
- Watch → Category (many-to-one)
- Order → Customer (many-to-one)
- OrderItem → Order (many-to-one)
- OrderItem → Watch (many-to-one)
- Inventory → Watch (one-to-one)

## Performance Considerations

- The system uses SQLite for simplicity, but can be configured for PostgreSQL/MySQL
- GraphQL queries are optimized with proper joins
- Visualization is done client-side in the browser
- For production use, consider adding caching and query optimization

## Next Steps

1. Try the demo queries to understand capabilities
2. Experiment with your own questions
3. Examine the generated GraphQL queries to learn the schema
4. Explore the generated charts in your browser
5. Modify the seed data to match your specific use case

## Support

For issues or questions:
1. Check the error messages - they're usually informative
2. Verify your API key is correct
3. Ensure all dependencies are installed
4. Check that the database was initialized properly
