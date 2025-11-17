from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List, Dict

class ArticleItem(BaseModel):
    source: str
    title: str
    url: HttpUrl
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    topics: List[str] = []
    raw: Dict = {}

class SocialPostItem(BaseModel):
    platform: str           # 'X' | 'TruthSocial'
    user_handle: str
    post_id: str
    url: HttpUrl
    posted_at: Optional[datetime] = None
    text_snippet: Optional[str] = None
    metrics: Dict = {}
    topics: List[str] = []
