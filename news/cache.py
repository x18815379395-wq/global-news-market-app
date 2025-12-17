"""
Simple in-memory/file-backed cache for pipeline outputs.

Inspired by BettaFish's lightweight/extensible philosophy, this cache now:
- Stores multiple market/limit combinations instead of a single payload
- Persists recent entries to disk with TTL-aware eviction
- Exposes a snapshot method for health/debug endpoints
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from news.models import ContentType, HealthStatus, Market, NewsItem, PipelineResult

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent
DEFAULT_CACHE_FILE = CACHE_DIR / ".pipeline_cache.json"


class PipelineCache:
    def __init__(self, ttl_seconds: int = 300, storage_path: Optional[Path] = None, max_entries: int = 4, max_memory_entries: int = 10) -> None:
        self.ttl_seconds = ttl_seconds
        self.storage_path = storage_path or DEFAULT_CACHE_FILE
        self.max_entries = max_entries
        self.max_memory_entries = max_memory_entries
        self._lock = threading.Lock()
        self._memory: Dict[str, Tuple[PipelineResult, float]] = {}

    def _key(self, markets: List[str], limit: int) -> str:
        # Pre-sort markets for consistent key generation
        return f"{','.join(sorted(markets))}:{limit}"

    def get(self, markets: List[str], limit: int) -> Optional[PipelineResult]:
        key = self._key(markets, limit)
        now = time.time()
        
        # First check memory cache
        with self._lock:
            entry = self._memory.get(key)
            if entry:
                result, ts = entry
                if now - ts < self.ttl_seconds:
                    return result
                # Remove expired entry from memory
                del self._memory[key]

        # Then check disk cache if memory cache miss
        disk_entries = self._load_disk_entries()
        if key in disk_entries:
            payload = disk_entries[key]
            ts = payload.get("ts", 0)
            if now - ts < self.ttl_seconds:
                try:
                    items = [_dict_to_item(item) for item in payload.get("items", [])]
                    health = [_dict_to_health(status) for status in payload.get("health", [])]
                    generated_at = datetime.fromisoformat(payload["generated_at"])
                    result = PipelineResult(items=items, generated_at=generated_at, health=health)
                    # Cache in memory for faster access next time
                    with self._lock:
                        self._memory[key] = (result, now)
                        self._prune_memory(now)
                    return result
                except Exception as exc:  # pragma: no cover - defensive
                    logger.debug("Failed to hydrate cache entry %s: %s", key, exc)
        return None

    def set(self, markets: List[str], limit: int, result: PipelineResult) -> None:
        key = self._key(markets, limit)
        now = time.time()
        
        # Update memory cache
        with self._lock:
            self._memory[key] = (result, now)
            self._prune_memory(now)

        # Update disk cache
        entry = {
            "generated_at": result.generated_at.isoformat(),
            "items": [_item_to_dict(item) for item in result.items],
            "health": [_health_to_dict(h) for h in result.health],
            "ts": now,
        }
        try:
            entries = self._load_disk_entries()
            entries[key] = entry
            entries = self._prune_entries(entries, now)
            self._write_disk_entries(entries)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Persisting cache failed: %s", exc)

    def snapshot(self) -> Dict[str, object]:
        """Return a lightweight view for health endpoints without exposing payload content."""
        now = time.time()
        
        # Get memory entries
        with self._lock:
            memory_entries = []
            for key, (result, ts) in list(self._memory.items()):
                age = now - ts
                if age < self.ttl_seconds:
                    memory_entries.append({
                        "key": key, 
                        "age_seconds": round(age, 2), 
                        "items": len(result.items)
                    })
                else:
                    # Remove expired entries during snapshot
                    del self._memory[key]

        # Get disk entries
        disk_entries = []
        for key, payload in self._load_disk_entries().items():
            age = now - payload.get("ts", now)
            if age < self.ttl_seconds:
                disk_entries.append({
                    "key": key, 
                    "age_seconds": round(age, 2), 
                    "items": len(payload.get("items", []))
                })

        return {
            "ttl_seconds": self.ttl_seconds,
            "storage_path": str(self.storage_path),
            "max_entries": self.max_entries,
            "max_memory_entries": self.max_memory_entries,
            "memory_entries": memory_entries,
            "disk_entries": disk_entries[:self.max_entries],
        }

    def _prune_memory(self, now: float) -> None:
        """Prune expired and excess entries from memory cache."""
        # Filter out expired entries
        valid_entries = [(key, entry) for key, entry in self._memory.items() 
                        if now - entry[1] < self.ttl_seconds]
        
        # If still too many entries, keep only the most recent ones
        if len(valid_entries) > self.max_memory_entries:
            # Sort by timestamp descending
            valid_entries.sort(key=lambda x: x[1][1], reverse=True)
            # Keep only the most recent entries
            valid_entries = valid_entries[:self.max_memory_entries]
            
            # Rebuild memory cache
            self._memory = {key: entry for key, entry in valid_entries}
        else:
            # Just update the memory cache with valid entries
            self._memory = {key: entry for key, entry in valid_entries}

    def _prune_entries(self, entries: Dict[str, Dict[str, object]], now: float) -> Dict[str, Dict[str, object]]:
        """Prune expired and excess entries from disk cache."""
        # Filter out expired entries
        filtered = {
            key: payload for key, payload in entries.items() 
            if now - payload.get("ts", 0) < self.ttl_seconds
        }
        
        # If still too many entries, keep only the most recent ones
        if len(filtered) > self.max_entries:
            # Sort by timestamp descending
            sorted_entries = sorted(filtered.items(), 
                                  key=lambda kv: kv[1].get("ts", 0), 
                                  reverse=True)
            # Keep only the most recent entries
            return dict(sorted_entries[:self.max_entries])
        
        return filtered

    def _load_disk_entries(self) -> Dict[str, Dict[str, object]]:
        if not self.storage_path.exists():
            return {}
        try:
            blob = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

        # Backward compatibility: old format stored a single entry
        if "entries" not in blob:
            if blob.get("key"):
                return {blob["key"]: blob}
            return {}

        return blob.get("entries", {})

    def _write_disk_entries(self, entries: Dict[str, Dict[str, object]]) -> None:
        payload = {"entries": entries, "version": 2}
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(json.dumps(payload, default=str), encoding="utf-8")


def _item_to_dict(item: NewsItem) -> Dict[str, object]:
    return {
        "title": item.title,
        "description": item.description,
        "url": item.url,
        "source": item.source,
        "content_type": item.content_type.value,
        "market": item.market.value,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "metadata": item.metadata,
        "topics": item.topics,
        "relevance_score": item.relevance_score,
        "semantic_similarity": item.semantic_similarity,
    }


def _health_to_dict(status: HealthStatus) -> Dict[str, object]:
    return {
        "name": status.name,
        "healthy": status.healthy,
        "last_error": status.last_error,
        "last_success": status.last_success.isoformat() if status.last_success else None,
        "items_last_fetch": status.items_last_fetch,
        "latency_ms": status.latency_ms,
        "extra": status.extra,
    }


def _dict_to_item(data: Dict[str, object]) -> NewsItem:
    published_at = data.get("published_at")
    dt = datetime.fromisoformat(published_at) if isinstance(published_at, str) else None
    return NewsItem(
        title=data.get("title") or "",
        description=data.get("description") or "",
        url=data.get("url") or "",
        source=data.get("source") or "",
        content_type=ContentType(data.get("content_type", ContentType.FINANCIAL_NEWS)),
        market=Market(data.get("market", Market.GLOBAL)),
        published_at=dt,
        metadata=data.get("metadata") or {},
        topics=data.get("topics") or [],
        relevance_score=data.get("relevance_score"),
        semantic_similarity=data.get("semantic_similarity"),
    )


def _dict_to_health(data: Dict[str, object]) -> HealthStatus:
    last_success = data.get("last_success")
    dt = datetime.fromisoformat(last_success) if isinstance(last_success, str) else None
    return HealthStatus(
        name=data.get("name") or "unknown",
        healthy=bool(data.get("healthy")),
        last_error=data.get("last_error"),
        last_success=dt,
        items_last_fetch=int(data.get("items_last_fetch", 0) or 0),
        latency_ms=data.get("latency_ms"),
        extra=data.get("extra") or {},
    )
