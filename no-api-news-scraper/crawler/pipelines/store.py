from sqlalchemy import create_engine, text

class Store:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, future=True)

    def upsert_article(self, it):
        sql = text("""
        CREATE TABLE IF NOT EXISTS articles (
          url TEXT PRIMARY KEY,
          source TEXT, title TEXT, author TEXT,
          published_at TIMESTAMP, summary TEXT, topics TEXT
        );""")
        with self.engine.begin() as cx:
            cx.execute(sql)
            cx.execute(text("""
            INSERT INTO articles (url,source,title,author,published_at,summary,topics)
            VALUES (:url,:source,:title,:author,:published_at,:summary,:topics)
            ON CONFLICT(url) DO UPDATE SET title=excluded.title, summary=excluded.summary
            """), {**it.model_dump(), "topics": ",".join(it.topics)})

    def upsert_post(self, it):
        sql = text("""
        CREATE TABLE IF NOT EXISTS social_posts (
          platform TEXT, post_id TEXT,
          user_handle TEXT, url TEXT,
          posted_at TIMESTAMP, text_snippet TEXT, metrics TEXT, topics TEXT,
          PRIMARY KEY (platform, post_id)
        );""")
        with self.engine.begin() as cx:
            cx.execute(sql)
            cx.execute(text("""
            INSERT INTO social_posts (platform,post_id,user_handle,url,posted_at,text_snippet,metrics,topics)
            VALUES (:platform,:post_id,:user_handle,:url,:posted_at,:text_snippet,:metrics,:topics)
            ON CONFLICT(platform,post_id) DO UPDATE SET text_snippet=excluded.text_snippet
            """), {**it.model_dump(), "metrics": str(it.metrics), "topics": ",".join(it.topics)})
