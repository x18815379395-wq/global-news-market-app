"""Utility functions and classes for HorizonScanner."""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("horizonscanner")


class SmartCache:
    """Simple thread-safe TTL cache used for expensive calls (news APIs)."""

    def __init__(self, ttl_seconds: int = 60):
        self.ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Any:
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            ts, value = item
            if time.time() - ts > self.ttl:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.time(), value)


def get_env(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get environment variable with optional validation.
    
    Args:
        name: Environment variable name.
        default: Default value if variable is not set.
        required: Whether the variable is required.
        
    Returns:
        The environment variable value or default.
    """
    env_value = os.getenv(name, default)
    if required and (not env_value or env_value.startswith("YOUR_")):
        logger.warning("Environment variable %s missing; falling back to mock data", name)
        return None
    return env_value


def get_current_timestamp() -> str:
    """Get current UTC timestamp in ISO format.
    
    Returns:
        ISO formatted timestamp string.
    """
    return datetime.now(timezone.utc).isoformat()
