# Documentation Index

Welcome to the Natural Language to GraphQL Enterprise Solution documentation. This index will help you find the information you need quickly.

## 📚 Documentation Files

### Getting Started
1. **[README.md](README.md)** - Start here!
   - Project overview
   - Features and architecture
   - Quick start guide
   - Basic usage examples

2. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick lookup
   - Installation commands
   - Common queries
   - Troubleshooting
   - File outputs

3. **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup
   - Step-by-step installation
   - Configuration options
   - Example queries by category
   - Advanced usage

### Understanding the System
4. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Deep dive
   - Technical architecture
   - Design decisions
   - Code quality practices
   - Future enhancements

5. **[WORKFLOW.md](WORKFLOW.md)** - How it works
   - End-to-end flow diagrams
   - Component interactions
   - Data flow by layer
   - Error handling

### Reference Materials
6. **[sample_queries.txt](sample_queries.txt)** - Query examples
   - 50+ example queries
   - Organized by category
   - Copy-paste ready

7. **[.env.example](.env.example)** - Configuration template
   - Required environment variables
   - API key setup
   - Optional settings

## 🗂️ Code Organization

### Core Application
- **[main.py](main.py)** - Application entry point
  - Interactive mode
  - Demo mode
  - Database initialization

- **[config.py](config.py)** - Configuration management
  - Environment variables
  - LLM settings
  - Database URL

- **[test_setup.py](test_setup.py)** - Setup verification
  - Dependency checks
  - Configuration validation
  - Database testing

### Database Layer (`database/`)
- **[models.py](database/models.py)** - SQLAlchemy ORM models
  - Brand, Category, Watch
  - Customer, Order, OrderItem
  - Inventory, Supplier

- **[connection.py](database/connection.py)** - Database connection
  - Engine management
  - Session handling
  - Initialization

- **[seed_data.py](database/seed_data.py)** - Mock data generation
  - Faker integration
  - Realistic data
  - Referential integrity

### GraphQL Layer (`graphql_layer/`)
- **[schema.py](graphql_layer/schema.py)** - Strawberry GraphQL
  - Type definitions
  - Query resolvers
  - Nested relationships
  - Aggregation queries

### Agent Layer (`agent/`)
- **[nl_to_graphql_agent.py](agent/nl_to_graphql_agent.py)** - Main agent
  - Query generation
  - Query execution
  - Visualization decision
  - Answer generation

- **[prompts.py](agent/prompts.py)** - LLM prompts
  - System prompts
  - Schema documentation
  - Example queries

### Visualization Layer (`visualization/`)
- **[chart_generator.py](visualization/chart_generator.py)** - Plotly charts
  - Bar, line, pie charts
  - Scatter, histogram
  - Table display
  - HTML export

## 📖 Reading Paths

### For First-Time Users
1. Read [README.md](README.md) for overview
2. Follow [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for installation
3. Run `python test_setup.py` to verify
4. Try queries from [sample_queries.txt](sample_queries.txt)
5. Explore [SETUP_GUIDE.md](SETUP_GUIDE.md) for more examples

### For Developers
1. Read [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for architecture
2. Study [WORKFLOW.md](WORKFLOW.md) for data flow
3. Examine code in order:
   - `database/models.py` - Data structure
   - `graphql_layer/schema.py` - API layer
   - `agent/nl_to_graphql_agent.py` - AI logic
   - `visualization/chart_generator.py` - Charts
4. Review [main.py](main.py) for integration

### For System Administrators
1. Check [SETUP_GUIDE.md](SETUP_GUIDE.md) for deployment
2. Review [config.py](config.py) for settings
3. Understand [.env.example](.env.example) for configuration
4. Use [test_setup.py](test_setup.py) for validation

### For Data Analysts
1. Browse [sample_queries.txt](sample_queries.txt) for query ideas
2. Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for chart types
3. Study `graphql_layer/schema.py` for available data
4. Explore `database/models.py` for data relationships

## 🎯 Quick Navigation

### I want to...

**Install the system**
→ [QUICK_REFERENCE.md](QUICK_REFERENCE.md) → Installation section

**Understand how it works**
→ [WORKFLOW.md](WORKFLOW.md) → End-to-End Flow

**See example queries**
→ [sample_queries.txt](sample_queries.txt)

**Troubleshoot issues**
→ [QUICK_REFERENCE.md](QUICK_REFERENCE.md) → Troubleshooting section

**Learn the architecture**
→ [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) → Architecture section

**Configure the system**
→ [SETUP_GUIDE.md](SETUP_GUIDE.md) → Configuration section

**Understand the database**
→ [database/models.py](database/models.py) + [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

**Learn GraphQL queries**
→ [graphql_layer/schema.py](graphql_layer/schema.py) + [agent/prompts.py](agent/prompts.py)

**Customize visualizations**
→ [visualization/chart_generator.py](visualization/chart_generator.py)

**Modify AI behavior**
→ [agent/prompts.py](agent/prompts.py) + [agent/nl_to_graphql_agent.py](agent/nl_to_graphql_agent.py)

## 📊 File Size & Complexity

| File | Lines | Complexity | Purpose |
|------|-------|------------|---------|
| main.py | ~150 | Medium | Application orchestration |
| database/models.py | ~200 | Medium | Data schema |
| database/seed_data.py | ~250 | Medium | Data generation |
| graphql_layer/schema.py | ~400 | High | API layer |
| agent/nl_to_graphql_agent.py | ~200 | High | AI logic |
| agent/prompts.py | ~300 | Low | Prompt templates |
| visualization/chart_generator.py | ~200 | Medium | Chart generation |

## 🔍 Search Guide

### Find information about...

**Installation**: README.md, QUICK_REFERENCE.md, SETUP_GUIDE.md
**Configuration**: config.py, .env.example, SETUP_GUIDE.md
**Database**: database/models.py, PROJECT_SUMMARY.md
**GraphQL**: graphql_layer/schema.py, agent/prompts.py
**AI Agent**: agent/nl_to_graphql_agent.py, WORKFLOW.md
**Visualizations**: visualization/chart_generator.py, QUICK_REFERENCE.md
**Examples**: sample_queries.txt, SETUP_GUIDE.md
**Architecture**: PROJECT_SUMMARY.md, WORKFLOW.md
**Troubleshooting**: QUICK_REFERENCE.md, SETUP_GUIDE.md
**Testing**: test_setup.py, SETUP_GUIDE.md

## 🚀 Common Tasks

### Task: Run the application
1. See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) → Running the Application
2. Command: `python main.py`

### Task: Add a new query type
1. Study [graphql_layer/schema.py](graphql_layer/schema.py) → Query class
2. Add new resolver method
3. Update [agent/prompts.py](agent/prompts.py) with new query info

### Task: Modify database schema
1. Edit [database/models.py](database/models.py)
2. Update [database/seed_data.py](database/seed_data.py)
3. Update [graphql_layer/schema.py](graphql_layer/schema.py)
4. Run `python main.py init` to recreate database

### Task: Change LLM provider
1. Edit `.env` file
2. Set `LLM_PROVIDER=anthropic` or `openai`
3. Set appropriate API key
4. Restart application

### Task: Customize chart appearance
1. Edit [visualization/chart_generator.py](visualization/chart_generator.py)
2. Modify Plotly configuration in chart methods
3. Update colors, fonts, layouts

## 📝 Documentation Standards

All documentation follows these principles:
- **Clear**: Easy to understand for target audience
- **Complete**: Covers all necessary information
- **Concise**: No unnecessary verbosity
- **Current**: Kept up-to-date with code
- **Consistent**: Same terminology throughout

## 🆘 Getting Help

1. **Check documentation** in this order:
   - QUICK_REFERENCE.md for quick answers
   - SETUP_GUIDE.md for detailed instructions
   - PROJECT_SUMMARY.md for technical details
   - WORKFLOW.md for understanding flow

2. **Run diagnostics**:
   ```bash
   python test_setup.py
   ```

3. **Check common issues**:
   - API key not configured → Edit .env
   - Dependencies missing → pip install -r requirements.txt
   - Database not found → python main.py init

4. **Review examples**:
   - sample_queries.txt for query ideas
   - SETUP_GUIDE.md for usage examples

## 📅 Version Information

- **Version**: 1.0.0
- **Last Updated**: 2024
- **Python**: 3.10+
- **Key Dependencies**:
  - SQLAlchemy 2.0+
  - Strawberry GraphQL 0.216+
  - LangChain 0.1+
  - Plotly 5.18+

## 🎓 Learning Resources

### Beginner Path
1. README.md → Overview
2. QUICK_REFERENCE.md → Hands-on
3. sample_queries.txt → Practice
4. SETUP_GUIDE.md → Deep dive

### Advanced Path
1. PROJECT_SUMMARY.md → Architecture
2. WORKFLOW.md → Internals
3. Source code → Implementation
4. Customization → Extensions

---

**Start here**: [README.md](README.md)

**Quick start**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

**Need help?**: [SETUP_GUIDE.md](SETUP_GUIDE.md) → Troubleshooting
