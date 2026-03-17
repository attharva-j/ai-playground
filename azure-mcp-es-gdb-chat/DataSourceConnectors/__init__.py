"""
Data source connectors package.
Includes read-only connectors for:
- Databricks (DBFS and SQL)
- GraphDB (Neo4j HTTP API)
- ElasticSearch (HTTP API)

The classes provide main read methods and rely on
environment variables for credentials and endpoints.

This package does NOT expose or log secrets. Use environment variables.
"""

from .databricks_connector import DatabricksConnector
from .graphdb_connector import GraphDBConnector
from .elasticsearch_connector import ElasticSearchConnector
from .ntlm_rest_connector import NTLMRestConnector
