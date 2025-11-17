"""
Pydantic models for crawler outputs.
These capture only metadata (title, snippet, URL) to comply with content policies.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, HttpUrl, field_validator


class ArticleItem(BaseModel):
    source: str
    title: str
    url: HttpUrl
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    topics: List[str] = []
    raw: Dict[str, str] = {}

    @field_validator("title", mode="before")
    @classmethod
    def _trim_title(cls, value: str) -> str:
        return (value or "").strip()


class SocialPostItem(BaseModel):
    platform: str
    user_handle: str
    post_id: str
    url: HttpUrl
    posted_at: Optional[datetime] = None
    text_snippet: Optional[str] = None
    metrics: Dict[str, str] = {}
    topics: List[str] = []

