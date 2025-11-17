"""
Backwards-compatible helpers so existing call sites can migrate gradually.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from news import get_health_snapshot, get_news
from news.models import ContentType, Market, NewsItem

logger = logging.getLogger(__name__)


def _default_markets() -> List[Market]:
    env_value = os.getenv("NEWS_DEFAULT_MARKETS")
    if env_value:
        mapped = []
        for token in env_value.split(","):
            token = token.strip().lower()
            try:
                mapped.append(Market(token))
            except ValueError:
                logger.warning("Unknown market token '%s' in NEWS_DEFAULT_MARKETS; skipping.", token)
        if mapped:
            return mapped
    return [Market.GLOBAL, Market.US, Market.A_SHARE]


class NewsSourceManagerV2:
    """
    Drop-in replacement for the legacy NewsSourceManager class.
    """

    def __init__(self, markets: Optional[List[Market]] = None) -> None:
        self.markets = markets or _default_markets()
        self._health_cache: List[Dict[str, Any]] = []

    def get_enhanced_news_data(self, target_count: int = 20) -> List[Dict[str, Any]]:
        try:
            result = get_news(self.markets, limit=target_count)
        except Exception as exc:  # pragma: no cover - guard for callers
            logger.error("News pipeline failed: %s", exc)
            return []

        self._health_cache = [status.__dict__ for status in result.health]
        return [_news_item_to_dict(item) for item in result.items]

    def get_health_snapshot(self) -> Dict[str, Any]:
        health = get_health_snapshot()
        payload = {
            entry.name: {
                "healthy": entry.healthy,
                "last_error": entry.last_error,
                "last_success": entry.last_success.isoformat() if entry.last_success else None,
                "items_last_fetch": entry.items_last_fetch,
                "latency_ms": entry.latency_ms,
            }
            for entry in health
        }
        payload["last_fetch"] = datetime.utcnow().isoformat()
        return payload


def _news_item_to_dict(item: NewsItem) -> Dict[str, Any]:
    return {
        "title": item.title,
        "description": item.description,
        "url": item.url,
        "source": item.source,
        "market": item.market.value,
        "publishedAt": item.published_at.isoformat() if item.published_at else None,
        "contentType": item.content_type.value,
        "relevance_score": item.relevance_score,
        "semantic_similarity": item.semantic_similarity,
        "topics": item.topics,
        "metadata": item.metadata,
        "fetchedAt": datetime.utcnow().isoformat(),
    }
