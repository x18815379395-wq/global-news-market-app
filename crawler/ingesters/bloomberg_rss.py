"""
Bloomberg RSS ingestion.
"""
from __future__ import annotations

from typing import List

from crawler.infra.http import HttpFetcher
from crawler.ingesters.rss_base import parse_feed_entries
from crawler.schemas.models import ArticleItem

BLOOMBERG_FEEDS = [
    "https://www.bloomberg.com/markets/rss",
    "https://www.bloomberg.com/politics/feeds/site.xml",
]


def fetch_bloomberg_rss(fetcher: HttpFetcher, limit_per_feed: int = 15) -> List[ArticleItem]:
    items: List[ArticleItem] = []
    for feed in BLOOMBERG_FEEDS:
        response = fetcher.fetch(feed)
        if not response:
            continue
        parsed = parse_feed_entries(response.content, "Bloomberg")
        items.extend(parsed[:limit_per_feed])
    return items
