"""
Backward-compatibility shim that routes legacy imports to the new news pipeline.

The historical codebase imported ``NewsSourceManager`` from this module and
expected methods such as ``get_enhanced_news_data`` / ``get_health_snapshot``.
Those behaviors now live in :mod:`news.legacy`, so this file simply re-exports
the new implementation while preserving the original API surface.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional

import argparse
import json
import os
from datetime import datetime

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

from news.legacy import NewsSourceManagerV2
from news.models import Market

if load_dotenv:
    load_dotenv(os.getenv("EARSOFFORTUNE_DOTENV", ".env"))

logger = logging.getLogger(__name__)


class NewsSourceManager(NewsSourceManagerV2):
    """
    Thin wrapper around :class:`news.legacy.NewsSourceManagerV2`.
    Accepts either :class:`news.models.Market` enums or raw strings for markets.
    """

    def __init__(self, markets: Optional[Iterable[Market | str]] = None) -> None:
        normalized = _normalize_markets(markets)
        super().__init__(markets=normalized)
        if markets and normalized is None:
            logger.warning("NewsSourceManager: falling back to default markets; unknown tokens supplied.")


def _normalize_markets(markets: Optional[Iterable[Market | str]]):
    if not markets:
        return None
    result: List[Market] = []
    for value in markets:
        if isinstance(value, Market):
            result.append(value)
            continue
        try:
            result.append(Market(str(value).lower()))
        except ValueError:
            logger.warning("NewsSourceManager: ignoring unknown market '%s'", value)
    return result or None


def get_enhanced_news_data(limit: int = 20) -> List[Dict[str, Any]]:
    manager = NewsSourceManager()
    return manager.get_enhanced_news_data(target_count=limit)


def _format_health(health: Dict[str, Any]) -> str:
    lines = []
    for name, payload in health.items():
        if name == "last_fetch":
            continue
        status = "OK" if payload.get("healthy") else "WARN"
        lines.append(
            f"- {name:25s} [{status}] items={payload.get('items_last_fetch', 0)} "
            f"latency={payload.get('latency_ms') or 0:.0f}ms last_success={payload.get('last_success')}"
        )
    lines.append(f"\nSnapshot generated at: {health.get('last_fetch', datetime.utcnow().isoformat())}")
    return "\n".join(lines)


def _parse_markets(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    tokens = [token.strip() for token in value.split(",") if token.strip()]
    return tokens or None


def main() -> None:
    parser = argparse.ArgumentParser(description="News pipeline compatibility shim helper.")
    parser.add_argument("--limit", type=int, default=20, help="Number of news items to request (default: 20).")
    parser.add_argument(
        "--markets",
        type=str,
        help="Comma-separated markets (e.g. global,us,a_share). Defaults to NEWS_DEFAULT_MARKETS env.",
    )
    parser.add_argument("--health", action="store_true", help="Only print adapter health snapshot.")
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print raw JSON payload instead of summarized lines (applies to both news and health).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Fetch data without persisting anything.")
    args = parser.parse_args()

    manager = NewsSourceManager(markets=_parse_markets(args.markets))

    if args.health:
        health = manager.get_health_snapshot()
        if args.raw:
            print(json.dumps(health, indent=2, ensure_ascii=False))
        else:
            print("Adapter health snapshot:")
            print(_format_health(health))
        return

    items = manager.get_enhanced_news_data(target_count=args.limit)
    if args.raw:
        print(json.dumps(items, indent=2, ensure_ascii=False))
    else:
        print(f"Fetched {len(items)} items via compatibility shim.")
        for idx, item in enumerate(items[: min(5, len(items))], start=1):
            title = item.get("title") or "Untitled"
            source = item.get("source") or "unknown"
            market = item.get("market") or "global"
            published = item.get("publishedAt") or "n/a"
            print(f"[{idx}] {title} ({source} · {market}) @ {published}")
        if not items:
            print(
                "\nNo news items returned. Ensure NEWS_SERVICE_API_KEY/NEWSAPI_API_KEY is set "
                "and HorizonScanner/news_sources.yaml defines at least one adapter."
            )
    if args.dry_run:
        return


if __name__ == "__main__":  # pragma: no cover - manual smoke test helper
    main()
