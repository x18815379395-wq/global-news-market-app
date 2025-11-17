"""
Semantic filtering + scoring for normalized news items.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Tuple

from news.models import ContentType, Market, NewsItem
from utils.keywords import A_SHARE_KEYWORDS


BASE_KEYWORDS = [
    "stock",
    "market",
    "finance",
    "economy",
    "tariff",
    "china",
    "fed",
    "inflation",
    "trade",
    "ipo",
    "earnings",
    "geopolitics",
]

MARKET_KEYWORDS: Dict[Market, List[str]] = {
    Market.A_SHARE: A_SHARE_KEYWORDS,
    Market.US: BASE_KEYWORDS + ["S&P", "Dow", "Treasury"],
    Market.JAPAN: BASE_KEYWORDS + ["Nikkei", "BOJ"],
    Market.KOREA: BASE_KEYWORDS + ["KOSPI", "Samsung"],
    Market.GLOBAL: BASE_KEYWORDS,
    Market.CRYPTO: ["bitcoin", "ethereum", "token", "defi"],
}


class SemanticScorer:
    def __init__(self, similarity_threshold: float = 0.01) -> None:
        self.similarity_threshold = similarity_threshold

    def score(self, item: NewsItem) -> Tuple[float, float]:
        keywords = MARKET_KEYWORDS.get(item.market, BASE_KEYWORDS)
        combined = f"{item.title} {item.description}".lower()
        matches = sum(1 for kw in keywords if kw.lower() in combined)
        similarity = matches / max(len(keywords), 1)
        base = 0.6 if item.content_type == ContentType.FINANCIAL_NEWS else 0.4
        recency_bonus = self._recency_boost(item.published_at)
        score = min(1.0, base + min(0.35, matches * 0.02) + recency_bonus)
        return similarity, score

    def is_relevant(self, similarity: float, item: NewsItem) -> bool:
        if item.content_type == ContentType.SOCIAL_MEDIA:
            return True
        return similarity >= self.similarity_threshold

    @staticmethod
    def _recency_boost(published_at):
        if not published_at:
            return 0.0
        if not published_at.tzinfo:
            published_at = published_at.replace(tzinfo=timezone.utc)
        hours_old = (datetime.now(timezone.utc) - published_at).total_seconds() / 3600.0
        if hours_old < 1:
            return 0.15
        if hours_old < 6:
            return 0.1
        if hours_old < 24:
            return 0.05
        return 0.0
