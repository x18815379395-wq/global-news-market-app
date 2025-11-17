import time
from types import SimpleNamespace

from ingesters import wsj_rss


def test_wsj_rss_fetch_parses_entry(monkeypatch):
    entry = SimpleNamespace(
        title="Sample Headline",
        link="https://example.com/a",
        author="Reporter",
        summary="Short summary",
        published_parsed=time.struct_time((2024, 1, 2, 3, 4, 5, 1, 2, -1)),
    )

    def fake_parse(_):
        return SimpleNamespace(entries=[entry])

    monkeypatch.setattr(wsj_rss.feedparser, "parse", fake_parse)

    items = list(wsj_rss.fetch("dummy-url"))
    assert len(items) == 1
    article = items[0]
    assert article.source == "WSJ"
    assert article.title == "Sample Headline"
    assert article.url == "https://example.com/a"
    assert article.author == "Reporter"
    assert article.summary == "Short summary"
