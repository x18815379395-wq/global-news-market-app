"""
High-level orchestration for the redesigned news pipeline.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from crawler.pipelines.dedupe import dedupe_by_key

from news.adapters.base import AdapterRegistry
from news.adapters.google_news import GoogleNewsRssAdapter
from news.adapters.news_service import NewsServiceAdapter
from news.adapters.rss import RssAdapter
from news.adapters.social import SocialAdapter
from news.adapters.yahoo_finance import YahooFinanceRssAdapter
from news.cache import PipelineCache
from news.config_loader import load_sources_config
from news.models import ContentType, FetchCriteria, HealthStatus, Market, NewsItem, PipelineResult
from news.scoring import SemanticScorer
from news.sentiment import SentimentAnalyzer
from news.scheduler import NewsScheduler

logger = logging.getLogger(__name__)

DEFAULT_NEWS_SOURCES = {
    Market.US.value: "the-wall-street-journal,bloomberg,reuters,financial-times,cnn,cnbc",
    Market.GLOBAL.value: "the-wall-street-journal,bloomberg,reuters,financial-times,cnn,cnbc",
    Market.JAPAN.value: "reuters,bloomberg",
    Market.KOREA.value: "reuters,bloomberg",
    Market.A_SHARE.value: "reuters,bloomberg,financial-times",
    Market.CRYPTO.value: "coindesk,the-block",
}


class NewsPipeline:
    def __init__(self) -> None:
        self.registry = AdapterRegistry()
        self.scorer = SemanticScorer()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.scheduler = NewsScheduler()
        self.config = load_sources_config()
        self.adapters = self._build_adapters()
        self._health: Dict[str, HealthStatus] = {}

    def _build_adapters(self):
        """Build all configured adapters for the news pipeline.
        
        Returns:
            List of configured adapters.
        """
        adapters = []
        adapters.extend(self._configure_google_rss())
        adapters.extend(self._configure_news_service())
        adapters.extend(self._configure_rss())
        adapters.extend(self._configure_yahoo_finance())
        adapters.extend(self._configure_social())
        if not adapters:
            logger.warning("No adapters configured for news pipeline")
        return adapters

    def _configure_google_rss(self):
        adapters = []
        google_section = self.config.get("google_news_rss", {})
        for name, cfg in google_section.items():
            queries = cfg.get("queries") or []
            if isinstance(cfg.get("query"), str):
                queries.append(cfg["query"])
            queries = [q for q in queries if isinstance(q, str)]
            if not queries:
                continue
            try:
                topics = cfg.get("topics") or []
                if isinstance(topics, str):
                    topics = [topics]
                topics = [topic for topic in topics if isinstance(topic, str)]
                adapters.append(
                    GoogleNewsRssAdapter(
                        queries=queries,
                        market=cfg.get("market", name),
                        display_name=cfg.get("display_name") or f"GoogleNews-{name}",
                        hl=cfg.get("hl", "en-US"),
                        gl=cfg.get("gl", "US"),
                        ceid=cfg.get("ceid", "US:en"),
                        user_agent=cfg.get("user_agent"),
                        min_delay=float(cfg.get("min_delay", 1.0)),
                        limit_per_query=int(cfg.get("limit", 18)),
                        topics=topics,
                        query_params=cfg.get("query_params") if isinstance(cfg.get("query_params"), dict) else None,
                    )
                )
            except Exception as exc:
                logger.warning("Failed to configure Google News adapter %s: %s", name, exc)
        return adapters

    def _configure_news_service(self):
        api_key = (
            self.config.get("global_settings", {}).get("news_api_key")
            or self.config.get("traditional_media", {}).get("news_api_key")
        )
        # Allow env overrides
        import os

        api_key = os.getenv("NEWS_SERVICE_API_KEY") or os.getenv("NEWSAPI_API_KEY") or api_key
        if not api_key:
            logger.info("News service adapter disabled (missing API key).")
            return []

        endpoint = "https://newsapi.org/v2/everything"
        traditional = self.config.get("traditional_media", {})
        default_sources = DEFAULT_NEWS_SOURCES.copy()
        for source_name, cfg in traditional.items():
            sources_override = cfg.get("sources_by_market")
            if isinstance(sources_override, dict):
                default_sources.update(sources_override)
        adapter = NewsServiceAdapter(
            endpoint=endpoint,
            api_key=api_key,
            sources_by_market=default_sources,
            default_sources=DEFAULT_NEWS_SOURCES.get(Market.GLOBAL.value, ""),
            rate_limit_seconds=1.0,
            page_size=int(self.config.get("global_settings", {}).get("news_page_size", 25) or 25),
            pages=int(self.config.get("global_settings", {}).get("news_pages", 2) or 2),
            lookback_days=int(self.config.get("global_settings", {}).get("news_days", 2) or 2),
        )
        return [adapter]

    def _configure_rss(self):
        adapters = []
        rss_section = self.config.get("rss_feeds") or self.config.get("traditional_media", {})
        for name, cfg in rss_section.items():
            feeds = cfg.get("feeds")
            if not feeds:
                continue
            try:
                adapters.append(
                    RssAdapter(
                        feeds=feeds,
                        source_name=cfg.get("display_name", name),
                        topics=cfg.get("topics"),
                        limit_per_feed=int(cfg.get("limit", 15)),
                        min_delay=float(cfg.get("min_delay", 1.5)),
                        user_agent=cfg.get("user_agent"),
                        market=cfg.get("market", "global"),
                    )
                )
            except Exception as exc:
                logger.warning("Failed to configure RSS adapter %s: %s", name, exc)
        return adapters

    def _configure_yahoo_finance(self):
        adapters = []
        yahoo_section = self.config.get("yahoo_finance", {})
        for name, cfg in yahoo_section.items():
            feeds = cfg.get("feeds")
            if not feeds:
                continue
            try:
                adapters.append(
                    YahooFinanceRssAdapter(
                        feeds=feeds,
                        source_name=cfg.get("display_name", name),
                        topics=cfg.get("topics"),
                        limit_per_feed=int(cfg.get("limit", 15)),
                        min_delay=float(cfg.get("min_delay", 1.5)),
                        user_agent=cfg.get("user_agent"),
                        market=cfg.get("market", "global"),
                    )
                )
            except Exception as exc:
                logger.warning("Failed to configure Yahoo Finance adapter %s: %s", name, exc)
        return adapters

    def _configure_social(self):
        adapters = []
        for name, cfg in self.config.get("social_media", {}).items():
            handle = cfg.get("handle")
            if not handle:
                continue
            adapters.append(
                SocialAdapter(
                    platform=cfg.get("platform", name),
                    handle=handle,
                    limit=int(cfg.get("limit", 6)),
                    market=cfg.get("market", "global"),
                )
            )
        return adapters

    def run(self, markets: Sequence[Market | str], *, limit: int, cache: PipelineCache) -> PipelineResult:
        normalized_markets = [self._ensure_market(m) for m in markets]
        cached = cache.get([m.value for m in normalized_markets], limit)
        if cached:
            return cached

        now = datetime.now(timezone.utc)
        criteria = FetchCriteria(markets=normalized_markets, limit=limit)
        results: List[NewsItem] = []
        health: List[HealthStatus] = []

        # Filter adapters that match the requested markets to avoid unnecessary work
        relevant_adapters = []
        for adapter in self.adapters:
            # Check if adapter's market matches any of the requested markets
            # This is a heuristic - actual filtering happens in adapter.fetch()
            if hasattr(adapter, 'market') and adapter.market in criteria.markets:
                relevant_adapters.append(adapter)
            else:
                # For adapters without a specific market (like Google News), include them
                relevant_adapters.append(adapter)

        # Register adapters with scheduler if not already registered
        for adapter in relevant_adapters:
            adapter_name = getattr(adapter, "name", repr(adapter))
            if not self.scheduler.get_source_schedule(adapter_name):
                self.scheduler.register_source(adapter_name)

        # Optimize thread pool size based on available adapters and system resources
        # Limit to a reasonable maximum to avoid system resource exhaustion
        import os
        cpu_count = os.cpu_count() or 2
        
        # More intelligent thread pool sizing:
        # - Base on relevant adapters count
        # - Consider CPU cores
        # - Add buffer for I/O bound operations
        adapter_count = len(relevant_adapters)
        max_workers = min(
            max(2, adapter_count),  # At least 2 workers, up to adapter count
            cpu_count * 3  # Allow more workers for I/O bound tasks
        )
        
        logger.info(f"Using {max_workers} workers for {adapter_count} adapters")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(adapter.fetch, criteria, now=now): adapter for adapter in relevant_adapters}
            for future in as_completed(future_map):
                adapter = future_map[future]
                try:
                    items, status = future.result()
                    logger.debug(f"Adapter {status.name} fetched {len(items)} items")
                except Exception as exc:  # pragma: no cover - safety net
                    status = HealthStatus(name=getattr(adapter, "name", repr(adapter)), healthy=False, last_error=str(exc))
                    items = []
                    logger.error(f"Adapter {getattr(adapter, 'name', repr(adapter))} failed: {exc}")
                
                # Update scheduler with health status
                self.scheduler.update_source_health(status)
                
                results.extend(items)
                health.append(status)
                self._health[status.name] = status

        processed = self._post_process(results, limit)
        result = PipelineResult(items=processed, generated_at=now, health=health)
        cache.set([m.value for m in normalized_markets], limit, result)
        return result

    def _post_process(self, items: List[NewsItem], limit: int) -> List[NewsItem]:
        # Step 1: Remove duplicates
        deduped = dedupe_by_key(items, key_fn=lambda item: item.url)
        
        # Step 2: Score and filter items by relevance
        scored: List[NewsItem] = []
        for item in deduped:
            similarity, score = self.scorer.score(item)
            if not self.scorer.is_relevant(similarity, item):
                continue
            item.semantic_similarity = similarity
            item.relevance_score = score
            scored.append(item)
        
        # Step 3: Analyze sentiment for all scored items
        sentiment_analyzed = self.sentiment_analyzer.analyze_batch(scored)
        
        # Step 4: Sort by relevance score and limit results
        sentiment_analyzed.sort(key=lambda itm: itm.relevance_score or 0, reverse=True)
        
        return sentiment_analyzed[:limit]

    def _ensure_market(self, value: Market | str) -> Market:
        """Ensure a market value is a valid Market enum.
        
        Args:
            value: Market enum or string representation.
            
        Returns:
            Valid Market enum.
        """
        if isinstance(value, Market):
            return value
        try:
            return Market(value)
        except ValueError:
            logger.warning("Unknown market '%s', defaulting to GLOBAL", value)
            return Market.GLOBAL

    def get_health(self) -> List[HealthStatus]:
        return list(self._health.values())
