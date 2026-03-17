import os
import json
import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

class DatabricksConnector:
    """
    Read-only connector for Databricks.

    Supports two modes:
    - Reading files from DBFS via REST API.
    - Executing SQL queries via Warehouse/SQL Endpoint.

    Requires the following environment variables:
    - DATABRICKS_HOST: e.g. https://<workspace-url>
    - DATABRICKS_TOKEN: Personal Access Token (PAT)
    - DATABRICKS_SQL_ENDPOINT_ID: SQL endpoint ID (optional if only using DBFS)
    """

    def __init__(self):
        self.base_url = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
        self.token = os.environ.get("DATABRICKS_TOKEN", "")
        self.sql_endpoint_id = os.environ.get("DATABRICKS_SQL_ENDPOINT_ID", "")
        if not self.base_url or not self.token:
            logger.warning("DATABRICKS_HOST or DATABRICKS_TOKEN not configured. Reads may fail.")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })

    # --- DBFS ---
    def read_dbfs_file_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read a DBFS file and return its contents as text."""
        # API: GET /api/2.0/dbfs/read
        url = f"{self.base_url}/api/2.0/dbfs/read"
        resp = self.session.get(url, params={"path": path})
        resp.raise_for_status()
        data = resp.json()
        # content comes base64-encoded
        import base64
        bytes_content = base64.b64decode(data.get("data", ""))
        return bytes_content.decode(encoding, errors="replace")

    # --- SQL ---
    def query_sql(self, sql: str, catalog: Optional[str] = None, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query in Databricks and return rows as dicts."""
        if not self.sql_endpoint_id:
            raise ValueError("DATABRICKS_SQL_ENDPOINT_ID required for SQL queries")
        url = f"{self.base_url}/api/2.0/sql/statements/"
        payload = {
            "statement": sql,
            "warehouse_id": self.sql_endpoint_id,
        }
        if catalog:
            payload["catalog"] = catalog
        if schema:
            payload["schema"] = schema
        r = self.session.post(url, data=json.dumps(payload))
        r.raise_for_status()
        res = r.json()
        statement_id = res.get("statement_id")
        # Poll result
        status_url = f"{url}{statement_id}"
        while True:
            sr = self.session.get(status_url)
            sr.raise_for_status()
            sdata = sr.json()
            state = sdata.get("status", {}).get("state")
            if state in {"SUCCEEDED", "FAILED", "CANCELED"}:
                break
            import time
            time.sleep(1)
        if state != "SUCCEEDED":
            raise RuntimeError(f"SQL statement ended with state {state}")
        # Format rows
        result = sdata.get("result", {})
        cols = [c.get("name") for c in result.get("manifest", {}).get("columns", [])]
        rows = []
        for r in result.get("data", []):
            row = {cols[i]: r[i] for i in range(len(cols))}
            rows.append(row)
        return rows