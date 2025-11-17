## Redesigned News Pipeline (beta)

This package contains the next-generation multi-source ingestion stack. Highlights:

- **Adapters** in `news/adapters/` normalize News-as-a-service providers, RSS feeds, and social headless collectors behind a shared protocol.
- **Config-driven**: `news/config_loader.py` reads `HorizonScanner/news_sources.yaml` and expands `${ENV}` placeholders so new feeds can be added without touching code.
- **Pipeline**: `news/pipeline.py` orchestrates adapters concurrently, dedupes results, applies market-aware semantic scoring, and persists cache/health telemetry.
- **Caching**: `news/cache.PipelineCache` stores recent payloads in-memory plus `news/.pipeline_cache.json` for warm starts.

### Usage

```python
from news import get_news, get_health_snapshot, Market

result = get_news([Market.US, Market.A_SHARE], limit=25)
for item in result.items:
    print(item.title, item.relevance_score)

health = get_health_snapshot()
```

### Integration notes

1. Provide `NEWS_SERVICE_API_KEY` (or `NEWSAPI_API_KEY`) in the environment to enable the News-as-a-service adapter.
2. Ensure `PyYAML` is installed if you want to keep using YAML configuration (otherwise the loader falls back to JSON parsing).
3. For legacy integrations that still expect `NewsSourceManager`, import `NewsSourceManagerV2` from `news.legacy` (or keep importing `news_sources.NewsSourceManager`, which now shims to the new class) until all call-sites use `news.get_news`.
4. To add a new source, append it to `HorizonScanner/news_sources.yaml` with an `adapter` section; no code change required for simple RSS additions. See `news/samples/news_sources.example.yaml` for a minimal template you can copy.
5. Consumers such as `ears_of_fortune_v2` respect the optional `NEWS_DEFAULT_MARKETS` env var (comma-separated, e.g. `global,us,a_share`). When unset, it falls back to `["global", "us", "a_share"]`.

### Tests

Run the focused unit suite (pure Python, no network calls):

```bash
python -m unittest news.tests.test_scoring news.tests.test_pipeline news.tests.test_legacy
```
