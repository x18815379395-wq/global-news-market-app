"""
Public API for the redesigned news pipeline.
"""
from __future__ import annotations

from typing import List, Optional

from news.cache import PipelineCache
from news.models import Market, PipelineResult
from news.pipeline import NewsPipeline
from news.settings import NewsSettings, load_settings
from news.status import build_status

SETTINGS: NewsSettings = load_settings()
_pipeline = NewsPipeline()
_cache = PipelineCache(
    ttl_seconds=SETTINGS.cache_ttl_seconds,
    storage_path=SETTINGS.cache_path,
    max_entries=SETTINGS.cache_max_entries,
)


def get_news(markets: Optional[List[Market]] = None, limit: Optional[int] = None) -> PipelineResult:
    """
    Fetch/cached aggregated news aligned with the new architecture.
    """
    resolved_markets = markets or SETTINGS.default_markets
    resolved_limit = limit if limit is not None else SETTINGS.pipeline_limit
    return _pipeline.run(resolved_markets, limit=resolved_limit, cache=_cache)


def get_health_snapshot():
    return _pipeline.get_health()


def get_pipeline_status():
    """Expose a structured status payload for health dashboards."""
    return build_status(_pipeline, _cache, SETTINGS)
