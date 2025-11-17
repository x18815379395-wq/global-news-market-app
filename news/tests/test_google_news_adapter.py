import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from news.adapters.google_news import GoogleNewsRssAdapter
from news.models import FetchCriteria, Market

SAMPLE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Google News - Markets</title>
    <link>https://news.google.com/search?q=markets</link>
    <item>
      <title>Stocks gain as inflation cools</title>
      <link>https://example.com/markets/fed</link>
      <pubDate>Mon, 25 Nov 2024 12:00:00 GMT</pubDate>
      <description>Investors react to the latest CPI report.</description>
      <guid isPermaLink="true">https://example.com/markets/fed</guid>
    </item>
  </channel>
</rss>
"""


class GoogleNewsAdapterTests(unittest.TestCase):
    @patch("news.adapters.google_news.HttpFetcher.fetch")
    def test_fetch_returns_items(self, mock_fetch):
        response = MagicMock()
        response.content = SAMPLE_FEED
        mock_fetch.return_value = response

        adapter = GoogleNewsRssAdapter(
            queries=["global markets"],
            market="global",
            display_name="GoogleNews-Global",
        )
        criteria = FetchCriteria(markets=[Market.GLOBAL])
        items, status = adapter.fetch(criteria, now=datetime.now(timezone.utc))

        self.assertTrue(status.healthy)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].source, "GoogleNews-Global")
        self.assertEqual(items[0].market, Market.GLOBAL)
        self.assertEqual(items[0].metadata.get("provider"), "google-news")

    @patch("news.adapters.google_news.HttpFetcher.fetch")
    def test_skip_when_market_not_requested(self, mock_fetch):
        adapter = GoogleNewsRssAdapter(
            queries=["global markets"],
            market="us",
        )
        criteria = FetchCriteria(markets=[Market.GLOBAL])

        items, status = adapter.fetch(criteria, now=datetime.now(timezone.utc))

        mock_fetch.assert_not_called()
        self.assertTrue(status.healthy)
        self.assertEqual(items, [])


if __name__ == "__main__":
    unittest.main()
