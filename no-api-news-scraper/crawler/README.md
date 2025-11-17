# No-API News & Social Public Scraper (MVP)

**No official APIs**. We only use **public RSS** (WSJ/FT/Bloomberg) and **public pages** (Truth Social / X) with **Playwright**.
We collect **metadata only** (title, url, published time, author, short summary/snippet). We **do not** log in, bypass paywalls,
or scrape protected full text. We obey `robots.txt` and respect rate limits.

## Quickstart
```bash
pip install -U pip -r requirements.txt
python -m playwright install --with-deps firefox
python tools/doctor.py
```

Expected success lines:
```
API Status Check:
  DeepSeek configured: True
  RSS sources: {'WSJ': True, 'Bloomberg': True, 'Financial Times': True}
  Truth Social: {'realDonaldTrump': True}
  Twitter scraper ready: True
```

See `config/crawler.yaml` and `config/selectors.yaml` to configure feeds, handles, and selectors.
