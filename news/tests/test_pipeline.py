import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from news.cache import PipelineCache
from news.models import ContentType, HealthStatus, Market, NewsItem
from news.pipeline import NewsPipeline


class _StaticAdapter:
    def __init__(self, name: str, items):
        self.name = name
        self._items = items

    def fetch(self, criteria, *, now):
        return list(self._items), HealthStatus(
            name=self.name,
            healthy=True,
            last_success=now,
            items_last_fetch=len(self._items),
        )


class PipelineTests(unittest.TestCase):
    @patch("news.pipeline.load_sources_config", return_value={})
    def test_pipeline_deduplicates_and_scores(self, _mock_config):
        adapter_items = [
            NewsItem(
                title="Fed cuts rates to calm markets",
                description="Central bank surprise move boosts stocks",
                url="https://example.com/fed",
                source="ExampleWire",
                market=Market.US,
                content_type=ContentType.FINANCIAL_NEWS,
                published_at=datetime.now(timezone.utc),
            ),
            NewsItem(
                title="Duplicate story should be removed",
                description="Same URL as first",
                url="https://example.com/fed",
                source="AnotherWire",
                market=Market.US,
                content_type=ContentType.FINANCIAL_NEWS,
            ),
        ]
        pipeline = NewsPipeline()
        pipeline.adapters = [_StaticAdapter("static", adapter_items)]
        cache = PipelineCache(ttl_seconds=0, storage_path=Path("news/.test_pipeline_cache.json"))

        result = pipeline.run([Market.US], limit=5, cache=cache)
        self.assertEqual(len(result.items), 1)
        item = result.items[0]
        self.assertGreater(item.relevance_score or 0, 0.6)
        self.assertEqual(item.url, "https://example.com/fed")


if __name__ == "__main__":
    unittest.main()
