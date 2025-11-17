from bs4 import BeautifulSoup
import json
from datetime import datetime, timezone

def parse_og_jsonld(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    out = {}
    ogt = soup.select_one('meta[property="og:title"]')
    ogd = soup.select_one('meta[property="og:description"], meta[name="description"]')
    out["title"] = ogt["content"].strip() if ogt and ogt.has_attr("content") else None
    out["summary"] = ogd["content"].strip() if ogd and ogd.has_attr("content") else None
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(tag.string or "{}")
            if isinstance(data, dict) and data.get("@type") in ("Article","NewsArticle"):
                author = data.get("author")
                if isinstance(author, dict):
                    out["author"] = author.get("name")
                elif isinstance(author, list) and author:
                    out["author"] = author[0].get("name")
                dt = data.get("datePublished") or data.get("dateModified")
                if dt:
                    out["published_at"] = datetime.fromisoformat(dt.replace("Z","+00:00")).astimezone(timezone.utc)
                break
        except Exception:
            continue
    return out
