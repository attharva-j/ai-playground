"""
Database Tool - Provides database query capabilities for agents.
"""

import sqlite3
import json
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path

@dataclass
class QueryResult:
    """Result of a database query."""
    success: bool
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    error: Optional[str] = None

class DatabaseTool:
    """
    Database tool for querying structured data.
    
    Supports SQLite databases and provides safe query execution
    with result formatting for agent consumption.
    """
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Ensure the database exists and create sample data if needed."""
        if not self.db_path.exists():
            self._create_sample_database()
    
    def _create_sample_database(self):
        """Create a sample database with financial data for demonstrations."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create companies table
        cursor.execute("""
            CREATE TABLE companies (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                sector TEXT NOT NULL,
                market_cap REAL,
                revenue REAL,
                employees INTEGER,
                founded_year INTEGER
            )
        """)
        
        # Create financial_metrics table
        cursor.execute("""
            CREATE TABLE financial_metrics (
                id INTEGER PRIMARY KEY,
                company_id INTEGER,
                year INTEGER,
                revenue REAL,
                profit REAL,
                debt REAL,
                cash REAL,
                FOREIGN KEY (company_id) REFERENCES companies (id)
            )
        """)
        
        # Insert sample data
        companies_data = [
            (1, "TechCorp Inc", "Technology", 150000000000, 50000000000, 100000, 1995),
            (2, "FinanceGlobal", "Financial Services", 80000000000, 25000000000, 50000, 1980),
            (3, "HealthcarePlus", "Healthcare", 120000000000, 35000000000, 75000, 1990),
            (4, "EnergyFuture", "Energy", 200000000000, 60000000000, 120000, 1970),
            (5, "RetailMega", "Retail", 90000000000, 30000000000, 200000, 1985)
        ]
        
        cursor.executemany("""
            INSERT INTO companies (id, name, sector, market_cap, revenue, employees, founded_year)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, companies_data)
        
        # Insert financial metrics for multiple years
        financial_data = []
        for company_id in range(1, 6):
            for year in range(2020, 2024):
                base_revenue = companies_data[company_id-1][4]  # Get revenue from companies data
                revenue = base_revenue * (1 + (year - 2020) * 0.05)  # 5% growth per year
                profit = revenue * 0.15  # 15% profit margin
                debt = revenue * 0.3     # 30% of revenue as debt
                cash = revenue * 0.1     # 10% of revenue as cash
                
                financial_data.append((company_id, year, revenue, profit, debt, cash))
        
        cursor.executemany("""
            INSERT INTO financial_metrics (company_id, year, revenue, profit, debt, cash)
            VALUES (?, ?, ?, ?, ?, ?)
        """, financial_data)
        
        conn.commit()
        conn.close()
        
        print(f"Created sample database at {self.db_path}")
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> QueryResult:
        """
        Execute a SQL query safely and return structured results.
        
        Args:
            query: SQL query to execute
            params: Optional parameters for the query
            
        Returns:
            QueryResult with data and metadata
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            
            # Execute query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Fetch results
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            data = [dict(row) for row in rows]
            columns = list(rows[0].keys()) if rows else []
            
            conn.close()
            
            return QueryResult(
                success=True,
                data=data,
                columns=columns,
                row_count=len(data)
            )
            
        except Exception as e:
            return QueryResult(
                success=False,
                data=[],
                columns=[],
                row_count=0,
                error=str(e)
            )
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get the schema information for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with schema information
        """
        query = f"PRAGMA table_info({table_name})"
        result = self.execute_query(query)
        
        if not result.success:
            return {"error": result.error}
        
        schema = {
            "table_name": table_name,
            "columns": []
        }
        
        for row in result.data:
            column_info = {
                "name": row["name"],
                "type": row["type"],
                "not_null": bool(row["notnull"]),
                "primary_key": bool(row["pk"])
            }
            schema["columns"].append(column_info)
        
        return schema
    
    def list_tables(self) -> List[str]:
        """
        List all tables in the database.
        
        Returns:
            List of table names
        """
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        result = self.execute_query(query)
        
        if result.success:
            return [row["name"] for row in result.data]
        else:
            return []
    
    def get_database_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the database structure and contents.
        
        Returns:
            Dictionary with database summary
        """
        tables = self.list_tables()
        summary = {
            "database_path": str(self.db_path),
            "table_count": len(tables),
            "tables": {}
        }
        
        for table in tables:
            schema = self.get_table_schema(table)
            
            # Get row count
            count_result = self.execute_query(f"SELECT COUNT(*) as count FROM {table}")
            row_count = count_result.data[0]["count"] if count_result.success else 0
            
            summary["tables"][table] = {
                "schema": schema,
                "row_count": row_count
            }
        
        return summary
    
    def format_results_for_agent(self, result: QueryResult, query: str) -> str:
        """
        Format query results in a way that's easy for agents to understand.
        
        Args:
            result: Query result to format
            query: Original query for context
            
        Returns:
            Formatted string representation
        """
        if not result.success:
            return f"Query failed: {result.error}\nQuery: {query}"
        
        if result.row_count == 0:
            return f"Query returned no results.\nQuery: {query}"
        
        formatted = f"Query Results ({result.row_count} rows):\n"
        formatted += f"Query: {query}\n\n"
        
        # Format as table if reasonable number of rows
        if result.row_count <= 10:
            # Create table header
            if result.columns:
                formatted += " | ".join(result.columns) + "\n"
                formatted += "-" * (len(" | ".join(result.columns))) + "\n"
                
                # Add data rows
                for row in result.data:
                    row_values = [str(row.get(col, "")) for col in result.columns]
                    formatted += " | ".join(row_values) + "\n"
        else:
            # For large results, show summary
            formatted += f"Large result set ({result.row_count} rows). Sample data:\n"
            for i, row in enumerate(result.data[:3]):
                formatted += f"Row {i+1}: {json.dumps(row, indent=2)}\n"
            formatted += f"... and {result.row_count - 3} more rows\n"
        
        return formatted
    
    def calculate_financial_ratio(self, company_name: str, year: int, ratio_type: str) -> Dict[str, Any]:
        """
        Calculate common financial ratios for a company.
        
        Args:
            company_name: Name of the company
            year: Year for the calculation
            ratio_type: Type of ratio (debt_to_equity, profit_margin, etc.)
            
        Returns:
            Dictionary with ratio calculation results
        """
        # Get company and financial data
        query = """
            SELECT c.name, c.market_cap, f.revenue, f.profit, f.debt, f.cash
            FROM companies c
            JOIN financial_metrics f ON c.id = f.company_id
            WHERE c.name = ? AND f.year = ?
        """
        
        result = self.execute_query(query, (company_name, year))
        
        if not result.success or result.row_count == 0:
            return {
                "error": f"No data found for {company_name} in {year}",
                "company": company_name,
                "year": year
            }
        
        data = result.data[0]
        
        ratios = {
            "company": company_name,
            "year": year,
            "data": data
        }
        
        # Calculate requested ratio
        if ratio_type == "profit_margin":
            ratios["profit_margin"] = (data["profit"] / data["revenue"]) * 100 if data["revenue"] > 0 else 0
            ratios["description"] = "Profit as percentage of revenue"
        
        elif ratio_type == "debt_to_revenue":
            ratios["debt_to_revenue"] = (data["debt"] / data["revenue"]) * 100 if data["revenue"] > 0 else 0
            ratios["description"] = "Debt as percentage of revenue"
        
        elif ratio_type == "cash_ratio":
            ratios["cash_ratio"] = (data["cash"] / data["revenue"]) * 100 if data["revenue"] > 0 else 0
            ratios["description"] = "Cash as percentage of revenue"
        
        else:
            ratios["error"] = f"Unknown ratio type: {ratio_type}"
        
        return ratios

# Example usage and testing
def test_database_tool():
    """Test function for database tool."""
    db_tool = DatabaseTool("data/sample_financial.db")
    
    # Test database summary
    summary = db_tool.get_database_summary()
    print("Database Summary:")
    print(json.dumps(summary, indent=2))
    
    # Test query
    result = db_tool.execute_query("SELECT name, sector, market_cap FROM companies LIMIT 3")
    formatted = db_tool.format_results_for_agent(result, "SELECT name, sector, market_cap FROM companies LIMIT 3")
    print("\nQuery Results:")
    print(formatted)
    
    # Test financial ratio calculation
    ratio = db_tool.calculate_financial_ratio("TechCorp Inc", 2023, "profit_margin")
    print("\nFinancial Ratio:")
    print(json.dumps(ratio, indent=2))

if __name__ == "__main__":
    test_database_tool()