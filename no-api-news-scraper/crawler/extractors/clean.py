from urllib.parse import urlsplit, urlunsplit

def normalize_url(url: str) -> str:
    parts = urlsplit(url)
    # strip query except essential bits if needed; keep scheme/host/path
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))

def clip(text: str, n: int = 800) -> str:
    return (text or "")[:n]
