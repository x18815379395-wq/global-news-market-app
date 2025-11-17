"""
Shared helpers for RSS ingestion.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable, List, Optional
from urllib.parse import urlsplit, urlunsplit

import feedparser

from crawler.schemas.models import ArticleItem

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    if not url:
        return url
    parts = urlsplit(url)
    # Remove tracking query parameters to aid dedupe
    query = ""
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


def parse_feed_entries(feed_content: bytes, source: str, topics: Optional[List[str]] = None) -> List[ArticleItem]:
    feed = feedparser.parse(feed_content)
    items: List[ArticleItem] = []
    for entry in getattr(feed, "entries", []):
        published_at = _parse_datetime(getattr(entry, "published_parsed", None))
        summary = getattr(entry, "summary", None) or getattr(entry, "description", None)
        if summary:
            summary = summary.strip()[:800]
        items.append(
            ArticleItem(
                source=source,
                title=getattr(entry, "title", "Untitled"),
                url=normalize_url(getattr(entry, "link", "")),
                author=getattr(entry, "author", None),
                published_at=published_at,
                summary=summary,
                topics=topics or [],
                raw={
                    "id": getattr(entry, "id", ""),
                },
            )
        )
    return items


def _parse_datetime(struct_time) -> Optional[datetime]:
    if not struct_time:
        return None
    return datetime(*struct_time[:6], tzinfo=timezone.utc)

