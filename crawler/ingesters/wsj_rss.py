"""
WSJ RSS ingestion.
"""
from __future__ import annotations

from typing import List

from crawler.infra.http import HttpFetcher
from crawler.ingesters.rss_base import parse_feed_entries
from crawler.schemas.models import ArticleItem

WSJ_FEEDS = [
    "https://feeds.a.dj.com/rss/WSJcomUSBusiness",
    "https://feeds.a.dj.com/rss/RSSMarketsMain",
]


def fetch_wsj_rss(fetcher: HttpFetcher, limit_per_feed: int = 15) -> List[ArticleItem]:
    items: List[ArticleItem] = []
    for feed in WSJ_FEEDS:
        response = fetcher.fetch(feed)
        if not response:
            continue
        parsed = parse_feed_entries(response.content, "WSJ")
        items.extend(parsed[:limit_per_feed])
    return items

