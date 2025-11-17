"""
Simple in-memory/file-backed cache for pipeline outputs.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from news.models import ContentType, HealthStatus, Market, NewsItem, PipelineResult

CACHE_DIR = Path(__file__).resolve().parent
DEFAULT_CACHE_FILE = CACHE_DIR / ".pipeline_cache.json"


class PipelineCache:
    def __init__(self, ttl_seconds: int = 300, storage_path: Optional[Path] = None) -> None:
        self.ttl_seconds = ttl_seconds
        self.storage_path = storage_path or DEFAULT_CACHE_FILE
        self._lock = threading.Lock()
        self._memory: Dict[str, Tuple[PipelineResult, float]] = {}

    def _key(self, markets: List[str], limit: int) -> str:
        return f"{','.join(sorted(markets))}:{limit}"

    def get(self, markets: List[str], limit: int) -> Optional[PipelineResult]:
        key = self._key(markets, limit)
        with self._lock:
            entry = self._memory.get(key)
            if entry and (time.time() - entry[1]) < self.ttl_seconds:
                return entry[0]
        # Allow cold start from disk
        if self.storage_path.exists():
            try:
                blob = json.loads(self.storage_path.read_text(encoding="utf-8"))
                if blob.get("key") == key and time.time() - blob.get("ts", 0) < self.ttl_seconds:
                    items = [_dict_to_item(item) for item in blob.get("items", [])]
                    health = [_dict_to_health(status) for status in blob.get("health", [])]
                    return PipelineResult(items=items, generated_at=datetime.fromisoformat(blob["generated_at"]), health=health)
            except Exception:
                pass
        return None

    def set(self, markets: List[str], limit: int, result: PipelineResult) -> None:
        key = self._key(markets, limit)
        with self._lock:
            self._memory[key] = (result, time.time())
        payload = {
            "key": key,
            "generated_at": result.generated_at.isoformat(),
            "items": [_item_to_dict(item) for item in result.items],
            "health": [_health_to_dict(h) for h in result.health],
            "ts": time.time(),
        }
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(payload, default=str), encoding="utf-8")
        except Exception:
            pass


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
