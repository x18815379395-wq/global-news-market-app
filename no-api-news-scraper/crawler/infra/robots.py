import urllib.robotparser as rp

_cache = {}

def allowed(url: str, user_agent: str) -> bool:
    from urllib.parse import urlparse
    u = urlparse(url)
    robots_url = f"{u.scheme}://{u.netloc}/robots.txt"
    if robots_url not in _cache:
        parser = rp.RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
        except Exception:
            _cache[robots_url] = None
            return True  # fail-open but can be adjusted per policy
        _cache[robots_url] = parser
    parser = _cache.get(robots_url)
    return True if parser is None else parser.can_fetch(user_agent, url)
