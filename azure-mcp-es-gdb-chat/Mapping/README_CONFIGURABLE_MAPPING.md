# Configurable PDF Mapping System

## Overview

This document describes the **Configurable PDF Mapping System** implemented for SmartPack generation. This system separates the data mapping logic from the code, allowing configuration changes through external JSON files without modifying Python code.

## Problem Statement

Previously, the mapping between Elasticsearch/API data (`summary` object) and PDF content (`pdf_content` object) was hardcoded in the `generate_summary` functions. This made it difficult to:
- Modify field mappings without changing code
- Maintain consistency across different entity types
- Quickly adapt to new data source structures
- Test different mapping configurations

## Solution Architecture

### Three-Stage Pipeline

The PDF generation process follows a three-stage pipeline:

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Elastic + API  │ ───> │     Summary     │ ───> │   PDF Content   │
│   (Raw Data)    │      │ (Intermediate)  │      │  (PDF Format)   │
└─────────────────┘      └─────────────────┘      └─────────────────┘
      STAGE 1                  STAGE 2                  STAGE 3
   (Not Modified)         (Not Modified)           (Not Modified)
                                  │
                                  │  Configurable Mapping
                                  │
                                  ▼
                        ┌─────────────────────┐
                        │  JSON Config Files  │
                        │  - company_mapping  │
                        │  - person_mapping   │
                        └─────────────────────┘
```

### Key Components

1. **`config_mapper.py`**: Core mapping engine that reads JSON configurations and applies path-based transformations
2. **`mapping_configs/`**: Directory containing JSON configuration files
   - `company_mapping.json`: Mapping rules for company SmartPacks
   - `person_mapping.json`: Mapping rules for person SmartPacks
3. **Modified `generate_summary` functions**: Updated to use the mapper instead of hardcoded logic

## How It Works

### 1. Configuration Files (JSON)

Configuration files define how to map data from the `summary` object to the `pdf_content` object using **path notation**.

#### Example: Company Mapping

```json
{
  "pdf_content_mappings": {
    "first_table": {
      "left_entries": [
        {
          "label": "Entity Type",
          "path": "key_information.Entity Type"
        },
        {
          "label": "No. of Employees",
          "path": "key_information.No. of Employees"
        }
      ]
    }
  }
}
```

This configuration tells the system:
- Look for data at `summary["key_information"]["Entity Type"]`
- Create a table entry with label "Entity Type" and the value found at that path

### 2. Path Resolution

The mapper uses **dot notation** to access nested dictionary values:

```python
# Configuration path: "key_information.Entity Type"
# Resolves to: summary["key_information"]["Entity Type"]

# Configuration path: "financials.Financials (general).current_year_revenue_usd"
# Resolves to: summary["financials"]["Financials (general)"]["current_year_revenue_usd"]
```

### 3. ConfigMapper Class

The `ConfigMapper` class provides methods to:

#### Core Methods
- **`get_value_by_path(data, path, default)`**: Retrieve values using path notation
- **`resolve_template(template, summary)`**: Replace `{{path}}` placeholders with actual values
- **`apply_mapping(summary, section)`**: Apply full configuration mapping

#### Specialized Builder Methods
- **`build_table_entries(summary, config)`**: Build table rows as list of tuples
- **`build_list_items(summary, config)`**: Build lists with fallback defaults
- **`format_investment_strategy_bullets(summary)`**: Format strategy as bullet points
- **`build_news_items(summary)`**: Build news items from array
- **`build_leadership_rows(summary)`**: Build leadership team rows
- **`build_board_rows(summary)`**: Build board member rows
- **`build_assignments_revenue_table(summary)`**: Build RRA assignments table (Person)
- **`build_rra_relationships_summary(summary)`**: Build RRA relationship lines (Person)
- **`build_recent_assignments(summary, type)`**: Build assignment lists (Person)

## Usage Examples

### Example 1: Adding a New Field to Company PDF

**Scenario**: Add a new field "Stock Symbol" to the company first table.

**Steps**:
1. Ensure the field exists in the `summary` object (e.g., `summary["key_information"]["Stock Symbol"]`)
2. Edit `mapping_configs/company_mapping.json`:

```json
{
  "pdf_content_mappings": {
    "first_table": {
      "left_entries": [
        // ... existing entries ...
        {
          "label": "Stock Symbol",
          "path": "key_information.Stock Symbol"
        }
      ]
    }
  }
}
```

3. No Python code changes needed!

### Example 2: Changing Data Source Path

**Scenario**: The API changes and "Headquarter" is now at `company_overview.headquarters` instead of `key_information.Headquarter`.

**Steps**:
1. Edit `mapping_configs/company_mapping.json`:

```json
{
  "pdf_content_mappings": {
    "first_table": {
      "right_entries": [
        {
          "label": "Headquarter",
          "path": "company_overview.headquarters"  // Changed path
        }
      ]
    }
  }
}
```

### Example 3: Using Template Placeholders

For dynamic text with multiple fields:

```json
{
  "summary_line": {
    "template": "Total Revenue: {{financials.revenue}} in {{financials.currency}}"
  }
}
```

The mapper will replace `{{financials.revenue}}` and `{{financials.currency}}` with actual values.

## File Structure

```
Mapping/
├── smartpack_entities.py          # Main entity classes with modified generate_summary
├── config_mapper.py               # Mapping engine
├── mapping_configs/               # Configuration directory
│   ├── company_mapping.json       # Company mapping rules
│   └── person_mapping.json        # Person mapping rules
└── README_CONFIGURABLE_MAPPING.md # This file
```

## Configuration Schema

### Basic Field Mapping

```json
{
  "label": "Field Label",
  "path": "path.to.data.in.summary"
}
```

### List Source with Default

```json
{
  "source": "path.to.list",
  "default": ["Default value if empty"]
}
```

### Template String

```json
{
  "template": "Fixed text with {{path.to.value}} placeholder"
}
```

### Complex Table Rows

```json
{
  "rows_source": "path.to.array",
  "row_mapping": {
    "target_field": "source_field_in_item",
    "another_target": "another_source"
  }
}
```

## Benefits

### 1. **Separation of Concerns**
- Data retrieval logic (Elastic/API) remains unchanged
- PDF generation logic remains unchanged
- Only mapping configuration changes

### 2. **Easy Maintenance**
- Non-developers can modify mappings
- No risk of breaking Python code
- Version control for mapping configurations

### 3. **Flexibility**
- Switch data sources without code changes
- A/B test different field presentations
- Quick adaptation to API changes

### 4. **Reusability**
- Same mapper works for company and person entities
- Specialized builder methods handle common patterns
- Easy to extend for new entity types

## Advanced Features

### Custom Builder Methods

The mapper includes specialized methods for complex data structures:

```python
# Company specific
mapper.format_investment_strategy_bullets(summary)
mapper.build_news_items(summary)
mapper.build_leadership_rows(summary)

# Person specific
mapper.build_assignments_revenue_table(summary)
mapper.build_rra_relationships_summary(summary)
mapper.build_recent_assignments(summary, "search_assignments")
```

### Fallback Handling

All mapping methods include intelligent fallback:
- If data not found at path → return default value
- If list is empty → return reference placeholder
- If structure invalid → return safe default

## Migration Path

### Before (Hardcoded)

```python
pdf_content = {
    "company": company_name,
    "first_table": {
        "left_entries": [
            ("Entity Type", str(key_info.get("Entity Type", "N/A"))),
            ("No. of Employees", str(key_info.get("No. of Employees", "N/A"))),
            # ... more hardcoded mappings
        ]
    }
}
```

### After (Configurable)

```python
mapper = load_mapper("company")
pdf_content = {
    "company": company_name,
    "first_table": {
        "left_entries": mapper.build_table_entries(
            summary,
            mapper.config.get("pdf_content_mappings", {})
                          .get("first_table", {})
                          .get("left_entries", [])
        )
    }
}
```

## Testing Your Configurations

### Validation Checklist

1. **Path Validity**: Ensure paths match your `summary` structure
2. **Type Matching**: Verify list/dict/string types match expectations
3. **Fallback Values**: Test with missing data to verify defaults work
4. **Edge Cases**: Test with empty lists, null values, missing keys

### Example Test

```python
# Test a specific path
mapper = load_mapper("company")
value = mapper.get_value_by_path(
    summary,
    "key_information.Entity Type",
    default="N/A"
)
print(f"Entity Type: {value}")
```

## Extending the System

### Adding a New Entity Type

1. Create `mapping_configs/new_entity_mapping.json`
2. Define your mapping structure following the schema
3. Use `load_mapper("new_entity")` in your code
4. Call appropriate builder methods

### Adding Custom Builder Methods

If you need specialized data transformation:

```python
# In config_mapper.py
def build_custom_structure(self, summary: Dict[str, Any]) -> Any:
    """
    Build custom data structure.
    """
    data = self.get_value_by_path(summary, "custom.path")
    # Your transformation logic
    return transformed_data
```

## Troubleshooting

### Issue: "Configuration file not found"
**Solution**: Check that JSON file exists in `mapping_configs/` directory

### Issue: "Path returns 'N/A' but data exists"
**Solution**: Verify path syntax matches dictionary structure exactly (case-sensitive)

### Issue: "TypeError in builder method"
**Solution**: Check that data type at path matches what builder expects (list vs dict vs string)

## Best Practices

1. **Use meaningful labels**: Make PDF labels clear and descriptive
2. **Document custom paths**: Add comments in JSON for non-obvious paths
3. **Test incrementally**: Change one mapping at a time and test
4. **Version your configs**: Use git to track configuration changes
5. **Validate JSON**: Ensure JSON is valid before deploying (use JSON validators)

## Summary

The Configurable PDF Mapping System provides:
- ✅ **Flexibility**: Change mappings without code changes
- ✅ **Maintainability**: Clear separation of concerns
- ✅ **Extensibility**: Easy to add new entities or fields
- ✅ **Safety**: Fallback handling prevents errors
- ✅ **Clarity**: Self-documenting configuration files

This system transforms rigid, hardcoded mappings into flexible, configuration-driven transformations that can adapt to changing requirements without developer intervention.

---

**Created**: 2025-12-10
**Version**: 1.0
**Author**: Claude Code (Anthropic)
