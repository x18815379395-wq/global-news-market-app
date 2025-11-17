from playwright.sync_api import sync_playwright
from schemas.models import SocialPostItem
from datetime import datetime, timezone
import time, random

def fetch_public_timeline(handle: str, selectors: dict, browser="firefox", headless=True, wait_after=2.5, limit=10):
    items=[]
    with sync_playwright() as p:
        b = getattr(p, browser).launch(headless=headless)
        ctx = b.new_context()
        page = ctx.new_page()
        page.goto(f"https://truthsocial.com/@{handle}", wait_until="domcontentloaded", timeout=30000)
        time.sleep(wait_after + random.random())
        cards = page.locator(selectors["article"]).all()[:limit]
        for c in cards:
            link = c.locator(f"a[href*='{selectors['link_contains']}']").first
            href = link.get_attribute("href") if link else None
            pid = href.split("/")[-1] if href else None
            t = c.locator(selectors["time"]).first
            dtiso = t.get_attribute("datetime") if t else None
            text = c.inner_text()[0:560]
            if href and pid:
                items.append(SocialPostItem(
                    platform="TruthSocial",
                    user_handle=handle,
                    post_id=pid,
                    url=f"https://truthsocial.com{href}",
                    posted_at=(datetime.fromisoformat(dtiso.replace("Z","+00:00")) if dtiso else None),
                    text_snippet=text
                ))
        ctx.close(); b.close()
    return items
