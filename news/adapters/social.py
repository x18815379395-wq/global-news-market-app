"""
Adapters wrapping existing headless social scrapers.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Callable, List, Optional, Tuple

from crawler.ingesters import x_web, truth_social_web
from crawler.schemas.models import SocialPostItem

from news.models import ContentType, FetchCriteria, HealthStatus, Market, NewsItem

logger = logging.getLogger(__name__)


class SocialAdapter:
    def __init__(
        self,
        platform: str,
        handle: str,
        limit: int = 8,
        market: str = "global",
    ) -> None:
        self.platform = platform.lower()
        self.handle = handle.lstrip("@")
        self.limit = limit
        self.market = Market(market) if market in Market._value2member_map_ else Market.GLOBAL

    @property
    def name(self) -> str:
        return f"{self.platform}:{self.handle}"

    def fetch(self, criteria: FetchCriteria, *, now: datetime) -> Tuple[List[NewsItem], HealthStatus]:
        if not criteria.include_social or self.market not in criteria.markets:
            return [], HealthStatus(name=self.name, healthy=True, items_last_fetch=0)

        start = time.time()
        last_error: Optional[str] = None
        posts: List[SocialPostItem] = []
        try:
            scraper = self._resolve_scraper()
            if scraper:
                posts = scraper(self.handle, limit=self.limit)
            else:
                last_error = f"{self.platform} scraper unavailable"
        except Exception as exc:  # pragma: no cover - headless env
            last_error = str(exc)
            logger.warning("%s scraping failed: %s", self.platform, exc)

        items = [
            NewsItem(
                title=f"{post.user_handle} ({post.platform})",
                description=post.text_snippet or "",
                url=str(post.url),
                source=f"{post.platform} @{post.user_handle}",
                market=self.market,
                content_type=ContentType.SOCIAL_MEDIA,
                published_at=post.posted_at,
                metadata={"post_id": post.post_id},
            )
            for post in posts
        ]
        healthy = bool(items) and last_error is None
        latency_ms = (time.time() - start) * 1000
        return items, HealthStatus(
            name=self.name,
            healthy=healthy,
            last_error=last_error,
            last_success=now if healthy else None,
            items_last_fetch=len(items),
            latency_ms=latency_ms,
        )

    def _resolve_scraper(self) -> Optional[Callable[..., List[SocialPostItem]]]:
        if self.platform in {"x", "twitter"}:
            if getattr(x_web, "PLAYWRIGHT_AVAILABLE", False):
                return x_web.fetch_x_public_timeline
            return None
        if self.platform in {"truth", "truthsocial"}:
            if getattr(truth_social_web, "PLAYWRIGHT_AVAILABLE", False):
                return truth_social_web.fetch_truth_public_timeline
            return None
        return None
