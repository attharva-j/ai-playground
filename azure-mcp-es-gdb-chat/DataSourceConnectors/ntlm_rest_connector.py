import logging
from typing import Any, Dict, Optional

import requests
from requests_ntlm import HttpNtlmAuth

logger = logging.getLogger(__name__)


class NTLMRestConnector:
    """
    Minimal NTLM-backed REST connector.

    Parameters are expected to come from Key Vault / env:
    - username/password (+ optional domain)
    - verify: whether to verify TLS certificates
    """

    def __init__(
        self,
        username: str,
        password: str,
        *,
        domain: Optional[str] = None,
        verify: bool = True,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        self.username = username
        self.password = password
        self.domain = domain
        self.verify = verify

        self.session = requests.Session()
        if self.username and self.password:
            user = f"{self.domain}\\{self.username}" if self.domain else self.username
            self.session.auth = HttpNtlmAuth(user, self.password)
        self.session.headers.setdefault("Content-Type", "application/json")
        if default_headers:
            self.session.headers.update(default_headers)

    def _resolve_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        url = self._resolve_url(path)
        logger.info("Calling NTLM REST endpoint: %s", url)
        resp = self.session.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json_body,
            headers=headers,
            timeout=timeout,
            verify=self.verify,
        )
        resp.raise_for_status()
        if not resp.text:
            return {}
        try:
            return resp.json()
        except Exception:
            # Fallback: return raw text so callers can debug mapping
            return {"text": resp.text}

    def get_json(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        return self.request_json("GET", path, params=params, headers=headers, timeout=timeout)

    def post_json(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ) -> Dict[str, Any]:
        return self.request_json("POST", path, params=params, json_body=json_body, headers=headers, timeout=timeout)
