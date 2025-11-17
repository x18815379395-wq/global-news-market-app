"""
Utilities for extracting metadata from OpenGraph + JSON-LD blocks.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, Optional

from bs4 import BeautifulSoup


def parse_metadata(html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "lxml")
    data: Dict[str, Optional[str]] = {
        "title": None,
        "summary": None,
        "author": None,
        "published_at": None,
    }

    og_title = soup.select_one('meta[property="og:title"]')
    if og_title and og_title.has_attr("content"):
        data["title"] = og_title["content"].strip()
    og_desc = soup.select_one('meta[property="og:description"], meta[name="description"]')
    if og_desc and og_desc.has_attr("content"):
        data["summary"] = og_desc["content"].strip()

    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(tag.string or "{}")
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list):
            candidates = [item for item in payload if isinstance(item, dict)]
        else:
            candidates = [payload] if isinstance(payload, dict) else []
        for candidate in candidates:
            if candidate.get("@type") in {"Article", "NewsArticle"}:
                author = candidate.get("author")
                if isinstance(author, dict):
                    data["author"] = author.get("name")
                elif isinstance(author, list) and author:
                    maybe = author[0]
                    if isinstance(maybe, dict):
                        data["author"] = maybe.get("name")
                    elif isinstance(maybe, str):
                        data["author"] = maybe
                published = candidate.get("datePublished") or candidate.get("dateModified")
                if published:
                    data["published_at"] = _safe_iso(published)
                headline = candidate.get("headline")
                if headline:
                    data["title"] = data["title"] or headline
                if not data["summary"]:
                    desc = candidate.get("description")
                    if isinstance(desc, str):
                        data["summary"] = desc.strip()
                return data
    return data


def _safe_iso(value: str) -> Optional[str]:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not dt.tzinfo:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return None

