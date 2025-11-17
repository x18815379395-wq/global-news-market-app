import click, yaml, pathlib
from ingesters import wsj_rss

@click.group()
def cli(): pass

@cli.command()
def wsj_once():
    cfg = yaml.safe_load(pathlib.Path("config/crawler.yaml").read_text(encoding="utf-8"))
    feeds = cfg["crawler"]["rss"]["WSJ"]["feeds"]
    for f in feeds:
        for it in wsj_rss.fetch(f):
            click.echo(it.model_dump_json())

if __name__ == "__main__":
    cli()
