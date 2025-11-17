"""
Simple token bucket style limiter shared across adapters.
"""
from __future__ import annotations

import threading
import time
from typing import Dict


class RateLimiter:
    def __init__(self) -> None:
        self._limits: Dict[str, float] = {}
        self._last_hit: Dict[str, float] = {}
        self._lock = threading.Lock()

    def configure(self, key: str, min_interval: float) -> None:
        self._limits[key] = min_interval

    def wait(self, key: str) -> None:
        interval = self._limits.get(key)
        if interval is None:
            return
        with self._lock:
            now = time.time()
            last = self._last_hit.get(key, 0.0)
            if now - last < interval:
                time.sleep(interval - (now - last))
            self._last_hit[key] = time.time()
