import httpx, time, random
from typing import Optional, Tuple

def get_text(url: str, ua: str, timeout: int = 25,
             etag: Optional[str] = None,
             last_mod: Optional[str] = None) -> Tuple[str, Optional[str], Optional[str]]:
    headers = {"User-Agent": ua}
    if etag: headers["If-None-Match"] = etag
    if last_mod: headers["If-Modified-Since"] = last_mod
    backoff = 1.0
    for _ in range(5):
        r = httpx.get(url, headers=headers, timeout=timeout)
        if r.status_code in (429, 503):
            time.sleep(min(60, backoff) + random.random())
            backoff *= 2
            continue
        r.raise_for_status()
        return r.text, r.headers.get("ETag"), r.headers.get("Last-Modified")
    raise RuntimeError(f"Too many retries: {url}")
