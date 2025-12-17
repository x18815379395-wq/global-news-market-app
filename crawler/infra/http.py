"""
Reusable HTTP fetching utilities with polite defaults (conditional requests, retries).
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

import requests


@dataclass
class CachedHeaders:
    etag: Optional[str] = None
    last_modified: Optional[str] = None


class HttpFetcher:
    """
    Thin wrapper over requests.Session supporting per-URL caching headers and polite throttling.
    """

    def __init__(
        self,
        user_agent: str,
        min_delay: float = 1.5,
        max_retries: int = 3,
        timeout: int = 20,
    ) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.8",
            }
        )
        self.min_delay = min_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self._last_hit: Dict[str, float] = {}
        self._cache: Dict[str, CachedHeaders] = {}
        self._lock = threading.RLock()

    def fetch(self, url: str, last_modified_time: Optional[datetime] = None) -> Optional[requests.Response]:
        """
        Fetch a URL politely. Respects cached ETag/Last-Modified headers.
        Returns None if 304 or request ultimately fails.
        
        Args:
            url: URL to fetch.
            last_modified_time: Optional. If provided, only fetch content modified after this time.
                This is used for incremental fetching.
                Note: Not all servers support this parameter.
        """
        for attempt in range(self.max_retries):
            self._respect_delay(url)
            headers = {}
            cached = self._cache.get(url)
            if cached:
                if cached.etag:
                    headers["If-None-Match"] = cached.etag
                if cached.last_modified:
                    headers["If-Modified-Since"] = cached.last_modified
            
            # Add custom last-modified header if provided
            if last_modified_time:
                headers["X-Last-Fetched"] = last_modified_time.isoformat()
                # For servers that support it, use If-Modified-Since with our last fetch time
                # but only if we don't already have a more recent Last-Modified header from the server
                if not cached or not cached.last_modified:
                    headers["If-Modified-Since"] = last_modified_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            try:
                response = self.session.get(url, headers=headers, timeout=self.timeout)
                if response.status_code == 304:
                    return None
                if response.status_code >= 400:
                    raise requests.HTTPError(f"HTTP {response.status_code}")
                self._remember_headers(url, response)
                return response
            except Exception:
                sleep_for = min(60, self.min_delay * (2 ** attempt))
                time.sleep(sleep_for + random.random())
        return None

    def _remember_headers(self, url: str, response: requests.Response) -> None:
        cached = self._cache.setdefault(url, CachedHeaders())
        cached.etag = response.headers.get("ETag") or cached.etag
        cached.last_modified = response.headers.get("Last-Modified") or cached.last_modified

    def _respect_delay(self, url: str) -> None:
        domain = self._extract_domain(url)
        with self._lock:
            last = self._last_hit.get(domain)
            now = time.time()
            if last and now - last < self.min_delay:
                wait = self.min_delay - (now - last) + random.random()
                time.sleep(wait)
            self._last_hit[domain] = time.time()

    @staticmethod
    def _extract_domain(url: str) -> str:
        return url.split("/")[2] if "://" in url else url

