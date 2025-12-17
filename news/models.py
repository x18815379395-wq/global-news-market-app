"""
Core data structures shared by the redesigned news pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class Market(str, Enum):
    GLOBAL = "global"
    US = "us"
    JAPAN = "japan"
    KOREA = "korea"
    A_SHARE = "a_share"
    EUROPE = "europe"
    INDIA = "india"
    AUSTRALIA = "australia"
    CRYPTO = "crypto"


class ContentType(str, Enum):
    FINANCIAL_NEWS = "financial-news"
    SOCIAL_MEDIA = "social-media"
    FALLBACK = "fallback"


@dataclass
class NewsItem:
    """
    Normalized representation of an article/post across all upstream sources.
    """

    title: str
    description: str
    url: str
    source: str
    content_type: ContentType = ContentType.FINANCIAL_NEWS
    market: Market = Market.GLOBAL
    published_at: Optional[datetime] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    topics: List[str] = field(default_factory=list)
    relevance_score: Optional[float] = None
    semantic_similarity: Optional[float] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    sentiment_dimensions: Dict[str, float] = field(default_factory=dict)


@dataclass
class FetchCriteria:
    markets: List[Market]
    limit: int = 30
    languages: Optional[List[str]] = None
    include_social: bool = True
    include_financial: bool = True


@dataclass
class HealthStatus:
    name: str
    healthy: bool
    last_error: Optional[str] = None
    last_success: Optional[datetime] = None
    items_last_fetch: int = 0
    latency_ms: Optional[float] = None
    extra: Dict[str, str] = field(default_factory=dict)


@dataclass
class PipelineResult:
    items: List[NewsItem]
    generated_at: datetime
    health: List[HealthStatus]
