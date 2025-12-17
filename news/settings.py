"""
Centralised settings for the news pipeline (env-first, code-light).

Values mirror BettaFish's approach of using OpenAI-compatible env keys and
lightweight overrides so deployments stay ergonomic.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from news.models import Market

logger = logging.getLogger(__name__)


@dataclass
class NewsSettings:
    default_markets: List[Market]
    pipeline_limit: int
    cache_ttl_seconds: int
    cache_path: Path
    cache_max_entries: int


def _int_from_env(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except Exception:
        logger.warning("Invalid int value for %s=%s; using default %s", key, raw, default)
        return default


def _parse_markets(raw: str | None) -> List[Market]:
    if not raw:
        return [Market.GLOBAL, Market.US, Market.A_SHARE]
    markets: List[Market] = []
    for token in raw.split(","):
        token = token.strip().lower()
        if not token:
            continue
        try:
            markets.append(Market(token))
        except ValueError:
            logger.warning("Unknown market token '%s' in NEWS_DEFAULT_MARKETS; skipping.", token)
    return markets or [Market.GLOBAL, Market.US, Market.A_SHARE]


def load_settings() -> NewsSettings:
    cache_path_env = os.getenv("NEWS_CACHE_PATH")
    cache_path = Path(cache_path_env) if cache_path_env else Path(__file__).resolve().parent / ".pipeline_cache.json"
    return NewsSettings(
        default_markets=_parse_markets(os.getenv("NEWS_DEFAULT_MARKETS")),
        pipeline_limit=_int_from_env("NEWS_PIPELINE_LIMIT", 20),
        cache_ttl_seconds=_int_from_env("NEWS_CACHE_TTL", 300),
        cache_path=cache_path,
        cache_max_entries=_int_from_env("NEWS_CACHE_MAX_ENTRIES", 4),
    )
