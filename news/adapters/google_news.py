"""
Adapter dedicated to Google News RSS queries.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode

from crawler.ingesters.rss_base import parse_feed_entries
from crawler.infra.http import HttpFetcher
from crawler.schemas.models import ArticleItem

from news.models import ContentType, FetchCriteria, HealthStatus, Market, NewsItem

logger = logging.getLogger(__name__)


def _ensure_market(value: str) -> Market:
    try:
        return Market(value)
    except ValueError:
        logger.warning("GoogleNews adapter received unknown market '%s'; defaulting to GLOBAL.", value)
        return Market.GLOBAL


class GoogleNewsRssAdapter:
    """
    Builds Google News RSS queries per market and normalizes the articles.
    """

    base_url = "https://news.google.com/rss/search"

    def __init__(
        self,
        queries: Iterable[str],
        market: str,
        display_name: Optional[str] = None,
        hl: str = "en-US",
        gl: str = "US",
        ceid: str = "US:en",
        user_agent: Optional[str] = None,
        min_delay: float = 1.0,
        limit_per_query: int = 20,
        topics: Optional[List[str]] = None,
        query_params: Optional[Dict[str, str]] = None,
    ) -> None:
        clean_queries: List[str] = []
        for raw in queries:
            if not isinstance(raw, str):
                continue
            token = raw.strip()
            if token:
                clean_queries.append(token)
        if not clean_queries:
            raise ValueError("GoogleNewsRssAdapter requires at least one query.")
        self.queries = clean_queries
        self.market = _ensure_market(market)
        self.display_name = display_name or f"GoogleNews-{self.market.value}"
        self.hl = hl
        self.gl = gl
        self.ceid = ceid
        self.fetcher = HttpFetcher(
            user_agent=user_agent
            or "HorizonScannerGoogleNews/1.0 (+https://example.com/compliance)",
            min_delay=min_delay,
        )
        self.limit_per_query = limit_per_query
        self.topics = topics or []
        self.query_params = query_params or {}
        self.name = self.display_name

    def fetch(self, criteria: FetchCriteria, *, now: datetime) -> Tuple[List[NewsItem], HealthStatus]:
        if self.market not in criteria.markets:
            return [], HealthStatus(name=self.name, healthy=True, items_last_fetch=0)

        start = time.time()
        collected: List[NewsItem] = []
        last_error: Optional[str] = None

        for query in self.queries:
            feed_url = self._build_feed_url(query)
            try:
                response = self.fetcher.fetch(feed_url)
                if not response:
                    continue
                entries: List[ArticleItem] = parse_feed_entries(response.content, self.display_name, self.topics)
                for article in entries[: self.limit_per_query]:
                    collected.append(
                        NewsItem(
                            title=article.title,
                            description=article.summary or "",
                            url=str(article.url),
                            source=self.display_name,
                            market=self.market,
                            topics=article.topics,
                            content_type=ContentType.FINANCIAL_NEWS,
                            published_at=article.published_at,
                            metadata={
                                "provider": "google-news",
                                "query": query,
                            },
                        )
                    )
            except Exception as exc:  # pragma: no cover - network errors
                last_error = str(exc)
                logger.warning("Google News RSS fetch failed for %s: %s", self.display_name, exc)

        healthy = bool(collected)
        status = HealthStatus(
            name=self.name,
            healthy=healthy,
            last_error=last_error,
            last_success=now if healthy else None,
            items_last_fetch=len(collected),
            latency_ms=(time.time() - start) * 1000,
        )
        return collected, status

    def _build_feed_url(self, query: str) -> str:
        params = {
            "q": query,
            "hl": self.hl,
            "gl": self.gl,
            "ceid": self.ceid,
        }
        params.update(self.query_params)
        return f"{self.base_url}?{urlencode(params)}"
