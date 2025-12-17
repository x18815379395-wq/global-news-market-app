import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import news_sources
from news.legacy import NewsSourceManagerV2
from news.models import ContentType, HealthStatus, Market, NewsItem, PipelineResult


class LegacyManagerTests(unittest.TestCase):
    @patch("news.legacy.get_health_snapshot")
    @patch("news.legacy.get_news")
    def test_get_enhanced_news_data_returns_serializable_dicts(self, mock_get_news, mock_health):
        item = NewsItem(
            title="Fed signals pause",
            description="Central bank hints at pause.",
            url="https://example.com/fed",
            source="ExampleWire",
            market=Market.US,
            content_type=ContentType.FINANCIAL_NEWS,
            published_at=datetime.now(timezone.utc),
            relevance_score=0.9,
            semantic_similarity=0.2,
        )
        pipeline_result = PipelineResult(
            items=[item],
            generated_at=datetime.now(timezone.utc),
            health=[],
        )
        mock_get_news.return_value = pipeline_result
        mock_health.return_value = [
            HealthStatus(name="static", healthy=True, items_last_fetch=1, last_success=datetime.now(timezone.utc))
        ]

        manager = NewsSourceManagerV2(markets=[Market.US])
        data = manager.get_enhanced_news_data(target_count=5)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Fed signals pause")
        self.assertEqual(data[0]["contentType"], ContentType.FINANCIAL_NEWS.value)
        health = manager.get_health_snapshot()
        self.assertIn("static", health)

    @patch("news_sources.NewsSourceManagerV2.__init__", return_value=None)
    def test_legacy_module_accepts_string_markets(self, mock_init):
        news_sources.NewsSourceManager(markets=["us", "global"])
        self.assertTrue(mock_init.called)


if __name__ == "__main__":
    unittest.main()
