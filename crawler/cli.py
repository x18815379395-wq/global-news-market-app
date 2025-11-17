"""
Simple CLI to trigger ingesters manually.
"""
from __future__ import annotations

import json
import os
import sys

import click

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from crawler.infra.http import HttpFetcher
from crawler.ingesters.wsj_rss import fetch_wsj_rss
from crawler.ingesters.x_web import fetch_x_public_timeline


@click.group()
def cli():
    pass


@cli.command()
@click.option("--feed", default="https://feeds.a.dj.com/rss/RSSMarketsMain")
def wsj_once(feed: str):
    fetcher = HttpFetcher(user_agent="HorizonScannerCrawler/1.0")
    articles = fetch_wsj_rss(fetcher)
    for article in articles[:5]:
        click.echo(json.dumps(article.model_dump(), ensure_ascii=False))


@cli.command()
@click.option("--handle", default="realDonaldTrump")
def x_once(handle: str):
    posts = fetch_x_public_timeline(handle, limit=3)
    for post in posts:
        click.echo(json.dumps(post.model_dump(), ensure_ascii=False))


if __name__ == "__main__":  # pragma: no cover
    cli()
