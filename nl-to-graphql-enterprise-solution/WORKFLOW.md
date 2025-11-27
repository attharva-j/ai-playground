# System Workflow Documentation

## End-to-End Query Processing Flow

### Step-by-Step Execution

```
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: User Input                                                  │
│ ─────────────────────────────────────────────────────────────────── │
│ User: "Show me the top 5 best-selling watch models"                │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: Natural Language Understanding                              │
│ ─────────────────────────────────────────────────────────────────── │
│ Agent analyzes query:                                               │
│ • Intent: Retrieve sales data                                       │
│ • Entity: Watch models                                              │
│ • Metric: Sales quantity                                            │
│ • Limit: Top 5                                                      │
│ • Sort: Descending by quantity                                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: GraphQL Query Generation (LLM)                              │
│ ─────────────────────────────────────────────────────────────────── │
│ Input: NL query + GraphQL schema documentation                      │
│ LLM: GPT-4 or Claude                                                │
│ Output:                                                             │
│   query {                                                           │
│     topSellingWatches(limit: 5) {                                   │
│       model_name                                                    │
│       brand_name                                                    │
│       total_quantity_sold                                           │
│       total_revenue                                                 │
│     }                                                               │
│   }                                                                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: GraphQL Query Execution                                     │
│ ─────────────────────────────────────────────────────────────────── │
│ Strawberry GraphQL processes query:                                 │
│ 1. Parse and validate query syntax                                  │
│ 2. Resolve topSellingWatches field                                  │
│ 3. Execute SQL query via SQLAlchemy:                                │
│    SELECT w.id, w.model_name, b.name,                               │
│           SUM(oi.quantity), SUM(oi.subtotal)                        │
│    FROM watches w                                                   │
│    JOIN order_items oi ON w.id = oi.watch_id                        │
│    JOIN brands b ON w.brand_id = b.id                               │
│    GROUP BY w.id                                                    │
│    ORDER BY SUM(oi.quantity) DESC                                   │
│    LIMIT 5                                                          │
│ 4. Return structured data                                           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 5: Data Retrieved                                              │
│ ─────────────────────────────────────────────────────────────────── │
│ {                                                                   │
│   "topSellingWatches": [                                            │
│     {                                                               │
│       "model_name": "Rolex Submariner",                             │
│       "brand_name": "Rolex",                                        │
│       "total_quantity_sold": 45,                                    │
│       "total_revenue": 1350000.00                                   │
│     },                                                              │
│     { ... 4 more items ... }                                        │
│   ]                                                                 │
│ }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 6: Visualization Decision (LLM)                                │
│ ─────────────────────────────────────────────────────────────────── │
│ Input: Original query + Data structure                              │
│ Analysis:                                                           │
│ • Data type: Categorical (watch models)                             │
│ • Metric: Numerical (quantity sold)                                 │
│ • Purpose: Comparison                                               │
│ • Best fit: Bar chart                                               │
│ Output:                                                             │
│ {                                                                   │
│   "chart_type": "bar",                                              │
│   "x_field": "model_name",                                          │
│   "y_field": "total_quantity_sold",                                 │
│   "title": "Top 5 Best-Selling Watch Models",                       │
│   "reasoning": "Bar chart best shows comparison of quantities"      │
│ }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 7: Chart Generation                                            │
│ ─────────────────────────────────────────────────────────────────── │
│ Plotly creates interactive bar chart:                               │
│ • X-axis: Watch model names                                         │
│ • Y-axis: Quantity sold                                             │
│ • Hover: Shows brand, quantity, revenue                             │
│ • Interactive: Zoom, pan, export                                    │
│ • Output: chart_bar.html                                            │
│                                                                     │
│   ┌─────────────────────────────────────────┐                      │
│   │ Top 5 Best-Selling Watch Models         │                      │
│   │                                          │                      │
│   │  50│     ▓▓▓▓                            │                      │
│   │  40│     ▓▓▓▓  ▓▓▓▓                      │                      │
│   │  30│     ▓▓▓▓  ▓▓▓▓  ▓▓▓▓                │                      │
│   │  20│     ▓▓▓▓  ▓▓▓▓  ▓▓▓▓  ▓▓▓▓  ▓▓▓▓    │                      │
│   │  10│     ▓▓▓▓  ▓▓▓▓  ▓▓▓▓  ▓▓▓▓  ▓▓▓▓    │                      │
│   │   0└─────────────────────────────────────│                      │
│   │      Sub   Speed  Carr  Navi  Tank      │                      │
│   └─────────────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 8: Natural Language Answer Generation (LLM)                    │
│ ─────────────────────────────────────────────────────────────────── │
│ Input: Original query + Retrieved data                              │
│ Output:                                                             │
│ "Based on the sales data, here are the top 5 best-selling watch    │
│ models:                                                             │
│                                                                     │
│ 1. Rolex Submariner - 45 units sold, generating $1,350,000         │
│ 2. Omega Speedmaster - 42 units sold, generating $840,000          │
│ 3. TAG Heuer Carrera - 38 units sold, generating $456,000          │
│ 4. Breitling Navitimer - 35 units sold, generating $525,000        │
│ 5. Cartier Tank - 33 units sold, generating $495,000               │
│                                                                     │
│ The Rolex Submariner is clearly the best performer, with both      │
│ the highest quantity sold and revenue generated."                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 9: Display Results to User                                     │
│ ─────────────────────────────────────────────────────────────────── │
│ Console Output:                                                     │
│ • Natural language answer                                           │
│ • Chart saved notification                                          │
│ • Option to view GraphQL query                                      │
│                                                                     │
│ Files Created:                                                      │
│ • chart_bar.html (interactive chart)                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Interaction Diagram

```
┌──────────────┐
│     USER     │
└──────┬───────┘
       │ Natural Language Query
       ▼
┌──────────────────────────────────────────────────────────────┐
│                    MAIN APPLICATION                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  main.py                                               │  │
│  │  • Handles user interaction                            │  │
│  │  • Orchestrates workflow                               │  │
│  │  • Displays results                                    │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   AGENT     │    │   GRAPHQL    │    │ VISUALIZE   │
│   LAYER     │◄───┤    LAYER     │───►│   LAYER     │
└─────────────┘    └──────────────┘    └─────────────┘
       │                   │
       │                   │
       ▼                   ▼
┌─────────────┐    ┌──────────────┐
│  LLM (GPT4/ │    │   DATABASE   │
│   Claude)   │    │    LAYER     │
└─────────────┘    └──────────────┘
```

## Data Flow by Layer

### 1. Agent Layer Flow
```
Natural Language Query
    │
    ├─► NL to GraphQL Agent
    │       │
    │       ├─► System Prompt + Schema Docs
    │       │       │
    │       │       ▼
    │       │   LLM (GPT-4/Claude)
    │       │       │
    │       │       ▼
    │       └─► GraphQL Query String
    │
    ├─► Execute GraphQL Query
    │       │
    │       ▼
    │   Retrieved Data
    │
    ├─► Visualization Decision
    │       │
    │       ├─► Data Summary + Query
    │       │       │
    │       │       ▼
    │       │   LLM Analysis
    │       │       │
    │       │       ▼
    │       └─► Chart Config
    │
    └─► Answer Generation
            │
            ├─► Data + Query
            │       │
            │       ▼
            │   LLM Synthesis
            │       │
            │       ▼
            └─► Natural Language Answer
```

### 2. GraphQL Layer Flow
```
GraphQL Query String
    │
    ├─► Strawberry Schema
    │       │
    │       ├─► Parse Query
    │       ├─► Validate Syntax
    │       ├─► Validate Types
    │       └─► Resolve Fields
    │
    ├─► Query Resolvers
    │       │
    │       ├─► topSellingWatches()
    │       ├─► revenueByMonth()
    │       ├─► watches()
    │       └─► customers()
    │
    └─► Database Query
            │
            ▼
        SQLAlchemy ORM
            │
            ▼
        SQL Execution
            │
            ▼
        Raw Data
            │
            ▼
        Type Conversion
            │
            ▼
        GraphQL Response
```

### 3. Database Layer Flow
```
SQLAlchemy Query
    │
    ├─► ORM Models
    │       │
    │       ├─► Brand
    │       ├─► Watch
    │       ├─► Customer
    │       ├─► Order
    │       └─► OrderItem
    │
    ├─► Relationships
    │       │
    │       ├─► Watch.brand
    │       ├─► Order.customer
    │       └─► Order.items
    │
    ├─► SQL Generation
    │       │
    │       ├─► SELECT statements
    │       ├─► JOIN clauses
    │       ├─► WHERE filters
    │       ├─► GROUP BY aggregations
    │       └─► ORDER BY sorting
    │
    └─► SQLite Execution
            │
            ▼
        Result Set
            │
            ▼
        ORM Objects
```

### 4. Visualization Layer Flow
```
Data + Chart Config
    │
    ├─► Chart Type Decision
    │       │
    │       ├─► Bar Chart
    │       ├─► Line Chart
    │       ├─► Pie Chart
    │       ├─► Scatter Plot
    │       ├─► Histogram
    │       └─► Table
    │
    ├─► Data Transformation
    │       │
    │       ├─► Extract fields
    │       ├─► Convert to DataFrame
    │       └─► Format values
    │
    ├─► Plotly Chart Creation
    │       │
    │       ├─► Configure axes
    │       ├─► Set colors/styles
    │       ├─► Add interactivity
    │       └─► Set layout
    │
    └─► Export
            │
            ├─► HTML file
            └─► Display in browser
```

## Error Handling Flow

```
Error Occurs
    │
    ├─► GraphQL Syntax Error
    │       │
    │       ├─► Log error
    │       ├─► Return error message
    │       └─► Suggest correction
    │
    ├─► Database Error
    │       │
    │       ├─► Rollback transaction
    │       ├─► Log error
    │       └─► Return user-friendly message
    │
    ├─► LLM API Error
    │       │
    │       ├─► Check API key
    │       ├─► Check rate limits
    │       └─► Retry with backoff
    │
    └─► Visualization Error
            │
            ├─► Fallback to table view
            └─► Log error details
```

## Performance Optimization Points

1. **Database Layer**
   - Indexed foreign keys
   - Efficient JOIN operations
   - Query result caching (future)

2. **GraphQL Layer**
   - Field-level resolution
   - DataLoader for N+1 prevention (future)
   - Query complexity limits (future)

3. **Agent Layer**
   - Temperature=0 for consistency
   - Cached schema documentation
   - Prompt optimization

4. **Visualization Layer**
   - Client-side rendering
   - Lazy loading for large datasets (future)
   - Chart caching (future)

## Scalability Considerations

```
Current: Single Process
    │
    ▼
Future: Microservices
    │
    ├─► API Gateway
    │       │
    │       ├─► GraphQL Service
    │       ├─► Agent Service
    │       └─► Visualization Service
    │
    ├─► Message Queue
    │       │
    │       └─► Async processing
    │
    └─► Caching Layer
            │
            ├─► Redis for queries
            └─► CDN for charts
```

## Security Flow

```
Request
    │
    ├─► Environment Variables
    │       │
    │       └─► API keys (not in code)
    │
    ├─► SQL Injection Prevention
    │       │
    │       └─► SQLAlchemy ORM (parameterized)
    │
    ├─► GraphQL Query Validation
    │       │
    │       └─► Type checking + limits
    │
    └─► Error Messages
            │
            └─► No sensitive data exposed
```

This workflow documentation provides a comprehensive view of how data flows through the system from user input to final visualization.
