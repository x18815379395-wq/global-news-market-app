"""
Financial Times RSS ingestion.
"""
from __future__ import annotations

from typing import List

from crawler.infra.http import HttpFetcher
from crawler.ingesters.rss_base import parse_feed_entries
from crawler.schemas.models import ArticleItem

FT_FEEDS = [
    "https://www.ft.com/?format=rss",
    "https://www.ft.com/markets?format=rss",
]


def fetch_ft_rss(fetcher: HttpFetcher, limit_per_feed: int = 15) -> List[ArticleItem]:
    items: List[ArticleItem] = []
    for feed in FT_FEEDS:
        response = fetcher.fetch(feed)
        if not response:
            continue
        parsed = parse_feed_entries(response.content, "Financial Times")
        items.extend(parsed[:limit_per_feed])
    return items

