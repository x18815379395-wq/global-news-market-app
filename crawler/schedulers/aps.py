"""
APScheduler entry points for running crawlers on a schedule.
"""
from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler

from crawler.infra.http import HttpFetcher
from crawler.ingesters.ft_rss import fetch_ft_rss
from crawler.ingesters.wsj_rss import fetch_wsj_rss
from crawler.ingesters.bloomberg_rss import fetch_bloomberg_rss
from crawler.ingesters.truth_social_web import fetch_truth_public_timeline
from crawler.ingesters.x_web import fetch_x_public_timeline
from crawler.pipelines.store import Store


def run_scheduler():
    fetcher = HttpFetcher(user_agent="HorizonScannerCrawler/1.0")
    store = Store()
    scheduler = BlockingScheduler(timezone="UTC")

    def job_rss():
        articles = []
        articles.extend(fetch_wsj_rss(fetcher))
        articles.extend(fetch_bloomberg_rss(fetcher))
        articles.extend(fetch_ft_rss(fetcher))
        store.upsert_articles(articles)

    def job_social():
        posts = []
        posts.extend(fetch_x_public_timeline("realDonaldTrump"))
        posts.extend(fetch_truth_public_timeline("realDonaldTrump"))
        store.upsert_social(posts)

    scheduler.add_job(job_rss, "cron", minute="*/20", id="rss_feeds")
    scheduler.add_job(job_social, "cron", minute="*/10", id="social_feeds")
    scheduler.start()


if __name__ == "__main__":  # pragma: no cover
    run_scheduler()
