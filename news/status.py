"""
Status/health helpers for the news pipeline.

The output is designed for API/UI consumption, mirroring BettaFish's
dependency-check style payloads while keeping data light-weight and redacted.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from news.cache import PipelineCache
from news.models import HealthStatus
from news.pipeline import NewsPipeline
from news.settings import NewsSettings


def _health_to_dict(status: HealthStatus) -> Dict[str, Any]:
    return {
        "name": status.name,
        "healthy": status.healthy,
        "last_error": status.last_error,
        "last_success": status.last_success.isoformat() if status.last_success else None,
        "items_last_fetch": status.items_last_fetch,
        "latency_ms": status.latency_ms,
        "extra": status.extra,
    }


def build_status(pipeline: NewsPipeline, cache: PipelineCache, settings: NewsSettings) -> Dict[str, Any]:
    health = [_health_to_dict(entry) for entry in pipeline.get_health()]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": {
            "health": health,
            "adapter_count": len(health),
            "default_markets": [m.value for m in settings.default_markets],
            "default_limit": settings.pipeline_limit,
        },
        "cache": cache.snapshot(),
        "config": {
            "cache_path": str(settings.cache_path),
            "cache_ttl_seconds": settings.cache_ttl_seconds,
            "cache_max_entries": settings.cache_max_entries,
        },
    }
