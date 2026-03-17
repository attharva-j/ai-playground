#!/usr/bin/env python3
"""
run_cypher.py — Standalone script to run a Cypher query against Neo4j and output JSON.

Requirements:
  pip install neo4j python-dotenv

Usage:
  python run_cypher.py -q "MATCH (n) RETURN n LIMIT 5" --pretty
  python run_cypher.py -q "MATCH (n) RETURN count(n) AS c" -o results.json

Environment:
  .env file in the same directory with:
    NEO4J_URL="<URL>"
    NEO4J_USER=<USER>
    NEO4J_PASSWORD=<PASS>
"""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv

# Reuse your existing connector
from DataSourceConnectors.graphdb_connector import GraphDBConnector

logger = logging.getLogger("run_cypher")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def _load_env() -> None:
    """Load variables from .env (silently if not present)."""
    load_dotenv(override=False)


def _get_credentials() -> Dict[str, str]:
    """Fetch required Neo4j creds from env; raise if missing."""
    url = os.getenv("NEO4J_URL")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    missing = [k for k, v in [("NEO4J_URL", url), ("NEO4J_USER", user), ("NEO4J_PASSWORD", password)] if not v]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Ensure your .env file defines them."
        )
    return {"url": url, "user": user, "password": password}


def _rows_via_connector(conn: GraphDBConnector, cypher: str) -> List[Dict[str, Any]]:
    """
    Execute a Cypher query and return rows as a list of dicts.

    Primary path: reuse GraphDBConnector.query_cypher().
    Fallback: use the neo4j driver directly if the connector's method expects
    an HTTP payload shape or raises unexpectedly.
    """
    try:
        rows = conn.query_cypher(cypher)
        # Some implementations may return None if they expect HTTP response shape
        if rows is not None and isinstance(rows, list):
            return rows
    except Exception as e:
        logger.debug("query_cypher() raised %s; falling back to driver.run()", e)

    # Fallback using the established driver/session (works with official neo4j driver)
    rows: List[Dict[str, Any]] = []
    with conn.driver.session() as session:
        result = session.run(cypher)
        for record in result:
            # record.data() returns a dict mapping column->value
            rows.append(record.data())
    return rows


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Run a Cypher query against Neo4j and output JSON.")
    parser.add_argument(
        "-q", "--query", required=True, help="Cypher query to execute (wrap in quotes)."
    )
    parser.add_argument(
        "-o", "--outfile", help="Optional output file path to write the JSON result."
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON."
    )
    args = parser.parse_args(argv)

    _load_env()
    creds = _get_credentials()

    logger.info("Connecting to Neo4j at %s", creds["url"])
    try: 
        connector = GraphDBConnector(creds["url"], creds["user"], creds["password"])
    except Exception:
        logger.info("Error connecting to Neo4j at %s", creds["url"])
        pass

    try:
        rows = _rows_via_connector(connector, args.query)
        # Ensure JSON serializable (e.g., Node/Relationship -> dict)
        def default_serializer(o):
            # Attempt to convert Neo4j graph types to plain dicts
            try:
                return dict(o)
            except Exception:
                return str(o)

        json_text = json.dumps(rows, indent=2 if args.pretty else None, default=default_serializer)

        if args.outfile:
            with open(args.outfile, "w", encoding="utf-8") as f:
                f.write(json_text)
            print(args.outfile)
            logger.info("Wrote %d row(s) to %s", len(rows), args.outfile)
        else:
            print("\n\n"+json_text)
            logger.info("Returned %d row(s) to stdout", len(rows))

        return 0
    finally:
        try:
            connector.driver.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))