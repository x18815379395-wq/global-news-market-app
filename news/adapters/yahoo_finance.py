"""
Adapter for Yahoo Finance RSS feeds.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import List, Optional, Tuple

from crawler.ingesters.rss_base import parse_feed_entries
from crawler.infra.http import HttpFetcher
from crawler.schemas.models import ArticleItem

from news.models import ContentType, FetchCriteria, HealthStatus, Market, NewsItem

logger = logging.getLogger(__name__)


class YahooFinanceRssAdapter:
    """
    Adapter for fetching and normalizing Yahoo Finance RSS feeds.
    """
    
    name = "yahoo_finance"
    
    def __init__(
        self,
        feeds: List[str],
        source_name: str = "Yahoo Finance",
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
            or "HorizonScannerYahooFinanceAdapter/1.0 (+https://example.com/compliance)",
            min_delay=min_delay,
        )
        self.market = Market(market) if market in Market._value2member_map_ else Market.GLOBAL
    
    def fetch(self, criteria: FetchCriteria, *, now: datetime) -> Tuple[List[NewsItem], HealthStatus]:
        """
        Fetch news from Yahoo Finance RSS feeds.
        
        Args:
            criteria: Fetch criteria.
            now: Current datetime.
            
        Returns:
            Tuple of list of NewsItems and HealthStatus.
        """
        if self.market not in criteria.markets:
            return [], HealthStatus(name=self.source_name, healthy=True, items_last_fetch=0)
        
        collected: List[NewsItem] = []
        start = time.time()
        last_error: Optional[str] = None
        
        # Get the last fetch time for this source (for incremental fetching)
        # For simplicity, we'll use the current time minus some buffer as initial value
        # In a production system, this would be stored persistently
        initial_last_fetch_time = now - timedelta(hours=1)
        
        for feed in self.feeds:
            try:
                # Use incremental fetching by providing the last fetch time
                response = self.fetcher.fetch(feed, last_modified_time=initial_last_fetch_time)
                if not response:
                    continue
                    
                articles: List[ArticleItem] = parse_feed_entries(response.content, self.source_name, self.topics)
                
                # Filter articles to only include those published after our last fetch time
                # This ensures we only get new articles
                new_articles = []
                for article in articles:
                    if article.published_at and article.published_at > initial_last_fetch_time:
                        new_articles.append(article)
                
                logger.debug(f"Found {len(new_articles)} new articles in {self.source_name} feed {feed}")
                
                for article in new_articles[: self.limit_per_feed]:
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
                            metadata={
                                "provider": "yahoo-finance",
                                "feed_url": feed,
                            },
                        )
                    )
            except Exception as exc:  # pragma: no cover - network
                last_error = str(exc)
                logger.warning("Yahoo Finance fetch failed for %s: %s", self.source_name, exc)
        
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