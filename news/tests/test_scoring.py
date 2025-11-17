import unittest
from datetime import datetime, timedelta, timezone

from news.models import ContentType, Market, NewsItem
from news.scoring import SemanticScorer


class SemanticScorerTests(unittest.TestCase):
    def test_financial_article_scores_higher_with_keywords(self):
        scorer = SemanticScorer()
        item = NewsItem(
            title="Fed hints at rate cut to calm stock market",
            description="Markets rally as economy data cools",
            url="https://example.com/fed",
            source="Example",
            market=Market.US,
            content_type=ContentType.FINANCIAL_NEWS,
            published_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        similarity, score = scorer.score(item)
        self.assertGreaterEqual(similarity, 0.01)
        self.assertGreater(score, 0.6)
        self.assertTrue(scorer.is_relevant(similarity, item))

    def test_non_matching_financial_article_filtered_out(self):
        scorer = SemanticScorer(similarity_threshold=0.05)
        item = NewsItem(
            title="Celebrity gossip roundup reaches new heights",
            description="Pop culture headlines dominate entertainment weekend",
            url="https://example.com/gossip",
            source="Example",
            market=Market.US,
            content_type=ContentType.FINANCIAL_NEWS,
        )
        similarity, score = scorer.score(item)
        self.assertFalse(scorer.is_relevant(similarity, item))
        self.assertLess(score, 0.65)


if __name__ == "__main__":
    unittest.main()
