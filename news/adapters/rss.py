"""
Adapter that fetches and normalizes RSS feeds using the existing crawler helpers.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from crawler.ingesters.rss_base import parse_feed_entries
from crawler.schemas.models import ArticleItem
from crawler.infra.http import HttpFetcher

from news.models import ContentType, FetchCriteria, HealthStatus, Market, NewsItem

logger = logging.getLogger(__name__)


class RssAdapter:
    name = "rss"

    def __init__(
        self,
        feeds: List[str],
        source_name: str,
        topics: Optional[List[str]] = None,
        limit_per_feed: int = 20,
        min_delay: float = 1.5,
        user_agent: Optional[str] = None,
        market: str = "global",
    ) -> None:
        self.feeds = feeds
        self.source_name = source_name
        self.topics = topics or []
        self.limit_per_feed = limit_per_feed
        self.fetcher = HttpFetcher(
            user_agent=user_agent
            or "HorizonScannerRssAdapter/1.0 (+https://example.com/compliance)",
            min_delay=min_delay,
        )
        self.market = Market(market) if market in Market._value2member_map_ else Market.GLOBAL

    def fetch(self, criteria: FetchCriteria, *, now: datetime) -> Tuple[List[NewsItem], HealthStatus]:
        if self.market not in criteria.markets:
            return [], HealthStatus(name=self.source_name, healthy=True, items_last_fetch=0)

        collected: List[NewsItem] = []
        start = time.time()
        last_error: Optional[str] = None
        for feed in self.feeds:
            try:
                response = self.fetcher.fetch(feed)
                if not response:
                    continue
                articles: List[ArticleItem] = parse_feed_entries(response.content, self.source_name, self.topics)
                for article in articles[: self.limit_per_feed]:
                    collected.append(
                        NewsItem(
                            title=article.title,
                            description=article.summary or "",
                            url=str(article.url),
                            source=self.source_name,
                            market=self.market,
                            topics=article.topics,
                            content_type=ContentType.FINANCIAL_NEWS,
                            published_at=article.published_at,
                        )
                    )
            except Exception as exc:  # pragma: no cover - network
                last_error = str(exc)
                logger.warning("RSS fetch failed for %s: %s", self.source_name, exc)

        healthy = bool(collected)
        latency_ms = (time.time() - start) * 1000
        return collected, HealthStatus(
            name=self.source_name,
            healthy=healthy,
            last_error=last_error,
            last_success=now if healthy else None,
            items_last_fetch=len(collected),
            latency_ms=latency_ms,
        )
