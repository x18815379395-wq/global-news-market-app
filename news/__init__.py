"""
Public API for the redesigned news pipeline.
"""
from __future__ import annotations

from typing import List, Optional

from news.cache import PipelineCache
from news.models import Market, PipelineResult
from news.pipeline import NewsPipeline

_pipeline = NewsPipeline()
_cache = PipelineCache()


def get_news(markets: Optional[List[Market]] = None, limit: int = 20) -> PipelineResult:
    """
    Fetch/cached aggregated news aligned with the new architecture.
    """
    return _pipeline.run(markets or [Market.GLOBAL], limit=limit, cache=_cache)


def get_health_snapshot():
    return _pipeline.get_health()
