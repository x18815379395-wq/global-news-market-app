import feedparser
from datetime import datetime, timezone
from schemas.models import ArticleItem
from extractors.clean import clip

def _dt(e):
    return datetime(*e.published_parsed[:6], tzinfo=timezone.utc) if getattr(e, "published_parsed", None) else None

def fetch(feed_url: str):
    feed = feedparser.parse(feed_url)
    for e in feed.entries:
        yield ArticleItem(
            source="WSJ",
            title=e.title,
            url=e.link,
            author=getattr(e, "author", None),
            published_at=_dt(e),
            summary=clip(getattr(e, "summary", None), 800)
        )
