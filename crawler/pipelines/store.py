"""
Lightweight SQLite storage for crawler outputs (metadata only).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from sqlalchemy import Column, DateTime, MetaData, String, Table, create_engine
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import Engine

from crawler.schemas.models import ArticleItem, SocialPostItem

metadata = MetaData()

articles_table = Table(
    "articles",
    metadata,
    Column("url", String, primary_key=True),
    Column("source", String, index=True),
    Column("title", String),
    Column("author", String, nullable=True),
    Column("published_at", DateTime, nullable=True),
    Column("summary", String, nullable=True),
    Column("topics", String, nullable=True),
)

social_table = Table(
    "social_posts",
    metadata,
    Column("platform", String, primary_key=True),
    Column("post_id", String, primary_key=True),
    Column("user_handle", String),
    Column("url", String),
    Column("posted_at", DateTime, nullable=True),
    Column("text_snippet", String, nullable=True),
    Column("metrics", String, nullable=True),
    Column("topics", String, nullable=True),
)


class Store:
    def __init__(self, db_path: str = "crawler_data.db") -> None:
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        metadata.create_all(self.engine)

    def upsert_articles(self, items: Iterable[ArticleItem]) -> None:
        with self.engine.begin() as conn:
            for item in items:
                stmt = insert(articles_table).values(
                    url=item.url,
                    source=item.source,
                    title=item.title,
                    author=item.author,
                    published_at=item.published_at,
                    summary=item.summary,
                    topics=",".join(item.topics or []),
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["url"],
                    set_={
                        "title": stmt.excluded.title,
                        "summary": stmt.excluded.summary,
                        "author": stmt.excluded.author,
                        "published_at": stmt.excluded.published_at,
                    },
                )
                conn.execute(stmt)

    def upsert_social(self, items: Iterable[SocialPostItem]) -> None:
        with self.engine.begin() as conn:
            for item in items:
                stmt = insert(social_table).values(
                    platform=item.platform,
                    post_id=item.post_id,
                    user_handle=item.user_handle,
                    url=item.url,
                    posted_at=item.posted_at,
                    text_snippet=item.text_snippet,
                    metrics=json.dumps(item.metrics or {}),
                    topics=",".join(item.topics or []),
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["platform", "post_id"],
                    set_={
                        "text_snippet": stmt.excluded.text_snippet,
                        "posted_at": stmt.excluded.posted_at,
                        "metrics": stmt.excluded.metrics,
                    },
                )
                conn.execute(stmt)

