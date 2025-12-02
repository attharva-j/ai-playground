"""
SQL Database Connector
Supports MySQL, PostgreSQL, Oracle, MS-SQL, Snowflake, Databricks, AWS RDS, GCP, Azure
"""

import os
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from cache.schema_cache import SchemaCache


class SQLConnector:
    """Connector for SQL databases with schema introspection"""
    
    def __init__(self, cache: SchemaCache):
        self.cache = cache
        self.engines: Dict[str, Engine] = {}
    
    async def get_schema(self, database_type: str) -> Dict[str, Any]:
        """Get database schema from cache or fetch it"""
        cache_key = f"sql_{database_type}"
        
        # Try cache first
        cached_schema = self.cache.get(cache_key)
        if cached_schema:
            return cached_schema
        
        # Fetch schema
        schema = await self._fetch_schema(database_type)
        
        # Cache it
        self.cache.set(cache_key, schema)
        
        return schema
    
    async def refresh_schema(self, database_type: str) -> None:
        """Force refresh of schema cache"""
        cache_key = f"sql_{database_type}"
        self.cache.invalidate(cache_key)
        await self.get_schema(database_type)
    
    async def _fetch_schema(self, database_type: str) -> Dict[str, Any]:
        """Fetch schema from database"""
        engine = self._get_engine(database_type)
        inspector = inspect(engine)
        
        schema = {
            "database_type": database_type,
            "tables": []
        }
        
        # Get all tables
        for table_name in inspector.get_table_names():
            table_info = {
                "name": table_name,
                "columns": [],
                "primary_keys": [],
                "foreign_keys": [],
                "indexes": []
            }
            
            # Get columns
            for column in inspector.get_columns(table_name):
                table_info["columns"].append({
                    "name": column["name"],
                    "type": str(column["type"]),
                    "nullable": column.get("nullable", True),
                    "default": column.get("default")
                })
            
            # Get primary keys
            pk = inspector.get_pk_constraint(table_name)
            if pk:
                table_info["primary_keys"] = pk.get("constrained_columns", [])
            
            # Get foreign keys
            for fk in inspector.get_foreign_keys(table_name):
                table_info["foreign_keys"].append({
                    "columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"]
                })
            
            # Get indexes
            for index in inspector.get_indexes(table_name):
                table_info["indexes"].append({
                    "name": index["name"],
                    "columns": index["column_names"],
                    "unique": index.get("unique", False)
                })
            
            schema["tables"].append(table_info)
        
        return schema
    
    async def execute_query(self, query: str, database_type: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        engine = self._get_engine(database_type)
        
        with engine.connect() as conn:
            result = conn.execute(text(query))
            
            # Convert to list of dicts
            columns = result.keys()
            rows = []
            for row in result:
                rows.append(dict(zip(columns, row)))
            
            return rows
    
    def _get_engine(self, database_type: str) -> Engine:
        """Get or create SQLAlchemy engine for database type"""
        if database_type in self.engines:
            return self.engines[database_type]
        
        connection_string = self._get_connection_string(database_type)
        engine = create_engine(connection_string)
        self.engines[database_type] = engine
        
        return engine
    
    def _get_connection_string(self, database_type: str) -> str:
        """Build connection string from environment variables"""
        db_type_upper = database_type.upper()
        
        if database_type == "mysql":
            host = os.getenv(f"{db_type_upper}_HOST", "localhost")
            port = os.getenv(f"{db_type_upper}_PORT", "3306")
            user = os.getenv(f"{db_type_upper}_USER", "root")
            password = os.getenv(f"{db_type_upper}_PASSWORD", "")
            database = os.getenv(f"{db_type_upper}_DATABASE", "")
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        
        elif database_type == "postgresql":
            host = os.getenv(f"{db_type_upper}_HOST", "localhost")
            port = os.getenv(f"{db_type_upper}_PORT", "5432")
            user = os.getenv(f"{db_type_upper}_USER", "postgres")
            password = os.getenv(f"{db_type_upper}_PASSWORD", "")
            database = os.getenv(f"{db_type_upper}_DATABASE", "")
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        elif database_type == "oracle":
            host = os.getenv(f"{db_type_upper}_HOST", "localhost")
            port = os.getenv(f"{db_type_upper}_PORT", "1521")
            user = os.getenv(f"{db_type_upper}_USER", "")
            password = os.getenv(f"{db_type_upper}_PASSWORD", "")
            service = os.getenv(f"{db_type_upper}_SERVICE", "")
            return f"oracle+cx_oracle://{user}:{password}@{host}:{port}/?service_name={service}"
        
        elif database_type == "mssql":
            host = os.getenv(f"{db_type_upper}_HOST", "localhost")
            port = os.getenv(f"{db_type_upper}_PORT", "1433")
            user = os.getenv(f"{db_type_upper}_USER", "")
            password = os.getenv(f"{db_type_upper}_PASSWORD", "")
            database = os.getenv(f"{db_type_upper}_DATABASE", "")
            return f"mssql+pyodbc://{user}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
        
        elif database_type == "snowflake":
            account = os.getenv("SNOWFLAKE_ACCOUNT", "")
            user = os.getenv("SNOWFLAKE_USER", "")
            password = os.getenv("SNOWFLAKE_PASSWORD", "")
            database = os.getenv("SNOWFLAKE_DATABASE", "")
            schema = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
            warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "")
            return f"snowflake://{user}:{password}@{account}/{database}/{schema}?warehouse={warehouse}"
        
        elif database_type == "databricks":
            host = os.getenv("DATABRICKS_HOST", "")
            http_path = os.getenv("DATABRICKS_HTTP_PATH", "")
            token = os.getenv("DATABRICKS_TOKEN", "")
            return f"databricks://token:{token}@{host}?http_path={http_path}"
        
        else:
            raise ValueError(f"Unsupported database type: {database_type}")
