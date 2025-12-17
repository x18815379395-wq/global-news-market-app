import json
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from news.cache import PipelineCache
from news.models import ContentType, HealthStatus, Market, NewsItem, PipelineResult


def _make_result(title: str) -> PipelineResult:
    now = datetime.now(timezone.utc)
    item = NewsItem(
        title=title,
        description="desc",
        url=f"https://example.com/{title}",
        source="unit",
        market=Market.GLOBAL,
        content_type=ContentType.FINANCIAL_NEWS,
        published_at=now,
    )
    health = [
        HealthStatus(
            name=f"{title}-adapter",
            healthy=True,
            last_success=now,
            items_last_fetch=1,
        )
    ]
    return PipelineResult(items=[item], generated_at=now, health=health)


class PipelineCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cache_path = Path(tempfile.gettempdir()) / "pipeline_cache_test.json"
        self.cache_path.unlink(missing_ok=True)

    def tearDown(self) -> None:
        self.cache_path.unlink(missing_ok=True)

    def test_persists_multiple_entries_and_evicts_oldest(self):
        cache = PipelineCache(ttl_seconds=60, storage_path=self.cache_path, max_entries=2)
        cache.set([Market.US.value], 5, _make_result("first"))
        cache.set([Market.GLOBAL.value], 3, _make_result("second"))

        self.assertIsNotNone(cache.get([Market.US.value], 5))
        self.assertIsNotNone(cache.get([Market.GLOBAL.value], 3))

        # Insert third entry -> oldest disk entry should be evicted to respect max_entries
        cache.set([Market.A_SHARE.value], 2, _make_result("third"))
        disk_entries = cache.snapshot()["disk_entries"]
        self.assertLessEqual(len(disk_entries), 2)
        self.assertIsNotNone(cache.get([Market.A_SHARE.value], 2))

    def test_reads_legacy_single_entry_format(self):
        legacy_payload = {
            "key": "global:5",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "items": [
                {
                    "title": "legacy",
                    "description": "desc",
                    "url": "https://example.com/legacy",
                    "source": "Legacy",
                    "content_type": ContentType.FINANCIAL_NEWS.value,
                    "market": Market.GLOBAL.value,
                    "published_at": datetime.now(timezone.utc).isoformat(),
                    "metadata": {},
                    "topics": [],
                    "relevance_score": 0.1,
                    "semantic_similarity": 0.1,
                }
            ],
            "health": [
                {
                    "name": "legacy-adapter",
                    "healthy": True,
                    "last_error": None,
                    "last_success": datetime.now(timezone.utc).isoformat(),
                    "items_last_fetch": 1,
                    "latency_ms": 12,
                    "extra": {},
                }
            ],
            "ts": time.time(),
        }
        self.cache_path.write_text(json.dumps(legacy_payload), encoding="utf-8")

        cache = PipelineCache(ttl_seconds=60, storage_path=self.cache_path, max_entries=2)
        result = cache.get([Market.GLOBAL.value], 5)
        self.assertIsNotNone(result)
        self.assertEqual(result.items[0].title, "legacy")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
