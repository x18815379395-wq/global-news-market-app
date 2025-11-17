"""
Adapter that talks to external News-as-a-service providers (e.g. NewsAPI).
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from news.http_client import HttpClient
from news.models import ContentType, FetchCriteria, HealthStatus, Market, NewsItem
from news.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class NewsServiceAdapter:
    """
    Thin wrapper around a REST news provider. Designed for NewsAPI-compatible schemas.
    """

    name = "news-service"

    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str],
        sources_by_market: Optional[Dict[str, str]] = None,
        default_sources: str = "",
        rate_limit_seconds: float = 1.0,
        page_size: int = 25,
        pages: int = 2,
        lookback_days: int = 2,
        language: str = "en",
        extra_params: Optional[Dict[str, str]] = None,
    ) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.sources_by_market = sources_by_market or {}
        self.default_sources = default_sources
        self.page_size = page_size
        self.pages = pages
        self.lookback_days = lookback_days
        self.language = language
        self.extra_params = extra_params or {}
        self.http = HttpClient()
        self.rate_limiter = RateLimiter()
        self.rate_limiter.configure(self.name, rate_limit_seconds)

    def fetch(self, criteria: FetchCriteria, *, now: datetime) -> Tuple[List[NewsItem], HealthStatus]:
        if not self.api_key:
            msg = "NEWS service API key missing"
            logger.warning(msg)
            return [], HealthStatus(name=self.name, healthy=False, last_error=msg)

        collected: List[NewsItem] = []
        last_error: Optional[str] = None
        start = time.time()
        for market in criteria.markets:
            sources = self.sources_by_market.get(market.value, self.default_sources)
            if not sources:
                continue

            for page in range(1, self.pages + 1):
                self.rate_limiter.wait(self.name)
                params = {
                    "sources": sources,
                    "language": self.language,
                    "sortBy": "publishedAt",
                    "pageSize": self.page_size,
                    "page": page,
                    "apiKey": self.api_key,
                    "from": (now - timedelta(days=self.lookback_days)).date().isoformat(),
                    "to": now.date().isoformat(),
                }
                params.update(self.extra_params)
                payload = self.http.get(self.endpoint, params=params)
                if not payload:
                    last_error = "Empty response"
                    break
                for article in payload.get("articles", []):
                    if not article.get("title") or not article.get("description"):
                        continue
                    collected.append(
                        NewsItem(
                            title=article["title"],
                            description=article["description"],
                            url=article["url"],
                            source=article.get("source", {}).get("name", "news"),
                            market=market,
                            content_type=ContentType.FINANCIAL_NEWS,
                            published_at=_parse_datetime(article.get("publishedAt")),
                            metadata={"provider": "newsapi"},
                        )
                    )

        healthy = bool(collected) and last_error is None
        latency_ms = (time.time() - start) * 1000
        return collected, HealthStatus(
            name=self.name,
            healthy=healthy,
            last_error=last_error,
            last_success=now if healthy else None,
            items_last_fetch=len(collected),
            latency_ms=latency_ms,
        )


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
