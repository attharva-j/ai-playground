import os
import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

class GraphDBConnector:
    """
    Read-only connector for a graph database via HTTP.

    Defaults to Neo4j Aura or Neo4j REST API (Bolt not supported here).
    Requires:
    - GRAPHDB_URL: base endpoint of the HTTP service
    - GRAPHDB_USER and GRAPHDB_PASSWORD: basic credentials

    Note: For production, use secure authentication and TLS connections.
    """

    def __init__(self, uri: str, username: str, password: str):
        self.base_url = uri
        self.user = username
        self.password = password
        if not self.base_url:
            logger.warning("GRAPHDB_URL not configured.")
        try:
            logger.info(f"tring to create for GraphDB ")
            self.driver = GraphDatabase.driver(self.base_url, auth=(self.user, self.password))
            logger.info(f"driver created for GraphDB test")
        except Exception as e:
            logger.info(f"not able to connect e: {e}")

    # Function to count and print the number of nodes
    def count_nodes(self, DB: str):
        #with self.driver.session(database=DB) as session:
        with self.driver.session(database=DB) as session:
            result = session.run("MATCH (n) RETURN count(n) AS node_count")
            count = result.single()["node_count"]
            print(f"Number of nodes in the database: {count}")

    def query_cypher(self, cypher: str, DB: str) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return a list of records (dict)."""
        # For Neo4j HTTP transactional endpoint
        # POST {url}/db/{database}/tx/commit
        try:
            logger.info(f"starting query inf Cypher in db {DB}")
            #with self.driver.session(database=DB) as session:
            with self.driver.session() as session:
                logger.info("starting query in Cypher")
                result = session.run(cypher)

                cols = result.keys()  # list of column names
                rows = []
                for record in result:   # record is a neo4j.Record
                    row = {col: record[col] for col in cols}
                    rows.append(row)

                logger.info(f"rows retrieved in graphDb: {rows}")
                return rows
        except Exception as e:
            logger.info(f"not able to connect e: {e}")