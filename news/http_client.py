"""
HTTP helper with retries + polite headers reused by adapters.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests
from urllib3.util.retry import Retry

from utils.security import redact_secrets

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, timeout: int = 15, max_retries: int = 3, user_agent: str | None = None):
        self.timeout = timeout
        self.session = requests.Session()
        retry = Retry(
            total=max_retries,
            backoff_factor=0.6,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        headers = {
            "User-Agent": user_agent or "HorizonScanner-NewsPipeline/1.0",
            "Accept": "application/json",
        }
        self.session.headers.update(headers)

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("HTTP GET failed %s %s", resp.status_code, redact_secrets(resp.text[:200]))
        except Exception as exc:
            logger.error("HTTP GET exception %s", redact_secrets(str(exc)))
        return None
