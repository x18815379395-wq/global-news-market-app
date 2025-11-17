"""
X (Twitter) public timeline scraping using Playwright headless browser.
Only collects metadata visible without login.
"""
from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from typing import List

from crawler.schemas.models import SocialPostItem

try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None  # type: ignore


def fetch_x_public_timeline(handle: str, limit: int = 8, polite_delay: float = 2.0) -> List[SocialPostItem]:
    if not PLAYWRIGHT_AVAILABLE:
        return []

    items: List[SocialPostItem] = []
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=30000)
        time.sleep(polite_delay + random.random())

        cards = page.locator("article").all()
        for card in cards[:limit]:
            link = card.locator("a[href*='/status/']").first
            href = link.get_attribute("href") if link else None
            if not href:
                continue
            post_id = href.rstrip("/").split("/")[-1]
            time_node = card.locator("time").first
            dtiso = time_node.get_attribute("datetime") if time_node else None
            snippet = card.inner_text().strip().replace("\u200b", "") if card else ""
            snippet = snippet[:560]

            items.append(
                SocialPostItem(
                    platform="X",
                    user_handle=handle,
                    post_id=post_id,
                    url=f"https://x.com{href}",
                    posted_at=_parse_iso(dtiso),
                    text_snippet=snippet,
                )
            )
        context.close()
        browser.close()
    return items


def _parse_iso(raw: str | None):
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

