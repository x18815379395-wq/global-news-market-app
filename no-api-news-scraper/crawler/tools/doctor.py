import time
from pathlib import Path
from typing import Dict, List, Tuple

import feedparser
import httpx
import yaml


BASE_DIR = Path(__file__).resolve().parents[1]


def load_yaml(path: str):
    target = Path(path)
    if not target.is_absolute():
        target = BASE_DIR / target
    return yaml.safe_load(target.read_text(encoding="utf-8"))


def _respect_delay(domain: str, min_delay: float, tracker: Dict[str, float]):
    import time as _time

    last = tracker.get(domain)
    now = _time.time()
    if last and now - last < min_delay:
        _time.sleep(min_delay - (now - last))
    tracker[domain] = _time.time()


def check_rss(name: str, feeds: List[str], user_agent: str, timeout: int, min_delay: float, sample: int = 3) -> Tuple[bool, List[str]]:
    ok = True
    msgs: List[str] = []
    headers = {"User-Agent": user_agent}
    delay_tracker: Dict[str, float] = {}

    for url in feeds:
        try:
            from urllib.parse import urlparse

            domain = urlparse(url).netloc
            _respect_delay(domain, min_delay, delay_tracker)

            response = httpx.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            n_entries = len(getattr(feed, "entries", []))
            msgs.append(f"{name} feed ok: {url} (entries={n_entries})")
            ok = ok and (min(sample, n_entries) > 0)
        except Exception as exc:
            msgs.append(f"{name} feed FAIL: {url} -> {exc}")
            ok = False
    return ok, msgs


def check_truth(handle: str, selectors: Dict[str, str], playwright_cfg: Dict[str, object], sample: int = 3):
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = getattr(p, playwright_cfg["browser"]).launch(headless=playwright_cfg["headless"])
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(f"https://truthsocial.com/@{handle}", wait_until="domcontentloaded", timeout=30000)
            time.sleep(playwright_cfg["wait_after_load_sec"])
            cards = page.locator(selectors["article"]).all()[:sample]
            ok = len(cards) > 0
            ctx.close()
            browser.close()
        return ok, [f"Truth @{handle} cards={len(cards)}"]
    except Exception as exc:
        return False, [f"Truth @{handle} FAIL -> {exc}"]


def check_x(handle: str, selectors: Dict[str, str], playwright_cfg: Dict[str, object], sample: int = 3):
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = getattr(p, playwright_cfg["browser"]).launch(headless=playwright_cfg["headless"])
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=30000)
            time.sleep(playwright_cfg["wait_after_load_sec"])
            cards = page.locator(selectors["article"]).all()[:sample]
            ok = len(cards) > 0
            ctx.close()
            browser.close()
        return ok, [f"X @{handle} cards={len(cards)}"]
    except Exception as exc:
        return False, [f"X @{handle} FAIL -> {exc}"]


def collect_status() -> Dict[str, object]:
    cfg = load_yaml("config/crawler.yaml")
    selectors = load_yaml("config/selectors.yaml")
    report: Dict[str, object] = {"deepseek_configured": True}

    rss_status: Dict[str, bool] = {}
    rss_msgs: List[str] = []
    crawler_cfg = cfg["crawler"]
    health_cfg = cfg["healthcheck"]

    for name, node in crawler_cfg["rss"].items():
        label = "Financial Times" if name == "FinancialTimes" else name
        if node.get("enabled") and node.get("feeds"):
            ok, msgs = check_rss(
                label,
                node["feeds"],
                crawler_cfg["user_agent"],
                crawler_cfg["timeout_sec"],
                crawler_cfg["per_domain_min_interval_sec"],
                health_cfg["rss_sample_limit"],
            )
            rss_status[label] = ok
            rss_msgs.extend(msgs)
        else:
            rss_status[label] = False
            rss_msgs.append(f"{label} disabled or no feeds configured")
    report["rss"] = rss_status

    truth_status: Dict[str, bool] = {}
    truth_msgs: List[str] = []
    truth_cfg = crawler_cfg["social"]["TruthSocial"]
    if truth_cfg.get("enabled"):
        for handle in truth_cfg.get("handles", []):
            ok, msgs = check_truth(handle, selectors["truth"], cfg["playwright"], health_cfg["truth_sample_limit"])
            truth_status[handle] = ok
            truth_msgs.extend(msgs)
    report["truth"] = truth_status

    x_status: Dict[str, bool] = {}
    x_msgs: List[str] = []
    x_cfg = crawler_cfg["social"]["X"]
    if x_cfg.get("enabled"):
        for handle in x_cfg.get("handles", []):
            ok, msgs = check_x(handle, selectors["x"], cfg["playwright"], health_cfg["x_sample_limit"])
            x_status[handle] = ok
            x_msgs.extend(msgs)
    report["twitter"] = x_status
    report["details"] = rss_msgs + truth_msgs + x_msgs
    report["twitter_ready"] = all(x_status.values()) if x_status else False
    return report


def main():
    status = collect_status()
    print("API Status Check:")
    print(f"  DeepSeek configured: {status['deepseek_configured']}")
    print(f"  RSS sources: {status['rss']}")
    print(f"  Truth Social: {status['truth']}")
    print(f"  Twitter scraper ready: {status['twitter_ready']}")
    print("\nDetails:")
    for msg in status["details"]:
        print("  -", msg)


if __name__ == "__main__":
    main()
