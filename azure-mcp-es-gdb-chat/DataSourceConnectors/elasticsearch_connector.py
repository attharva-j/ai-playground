import os
import logging
from typing import Any, Dict, List, Optional

import requests
import json

logger = logging.getLogger(__name__)

class ElasticSearchConnector:
    """
    Read-only connector for ElasticSearch via HTTP.

    Requires the following environment variables:
    - ELASTIC_URL: base endpoint, e.g. https://es-host:9200
    - ELASTIC_USER and ELASTIC_PASSWORD: credentials (optional)

    Read operations only: get document and search.
    """

    def __init__(self, base_url: str, user: str, password: str):
        self.base_url = base_url
        self.user = user
        self.password = password
        if not self.base_url:
            logger.warning("ELASTIC_URL not configured.")
        self.session = requests.Session()
        if self.user and self.password:
            self.session.auth = (self.user, self.password)
        self.session.headers.update({"Content-Type": "application/json"})

    def get_document(self, index: str, doc_id: str) -> Dict[str, Any]:
        """Get a document by ID."""
        url = f"{self.base_url}/{index}/_doc/{doc_id}"
        r = self.session.get(url)
        r.raise_for_status()
        return r.json()

    def search(self, index: str, query: Dict[str, Any], size: int = 10) -> Dict[str, Any]:
        """Run a search on an index."""
        url = f"{self.base_url}/{index}/_search"
        
        payload = query.copy()
        payload["size"] = size
        
        r = self.session.post(url, json=payload)
        r.raise_for_status()
        return r.json()