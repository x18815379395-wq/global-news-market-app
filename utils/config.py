import os


def get_int_env(name: str, default: int) -> int:
    try:
        v = os.getenv(name)
        return int(v) if v is not None and str(v).strip() != "" else default
    except Exception:
        return default


def get_collection_config() -> dict:
    """Centralized config for news collection parameters (env-overridable)."""
    return {
        # NewsAPI
        'news_pages': get_int_env('NEWS_PAGES', 3),
        'news_page_size': get_int_env('NEWS_PAGE_SIZE', 25),
        'news_days': get_int_env('NEWS_DAYS', 2),

        # Tavily
        'tavily_max_results': get_int_env('TAVILY_MAX_RESULTS', 15),
        'tavily_days': get_int_env('TAVILY_DAYS', 2),

        # Google Custom Search
        'cse_pages': get_int_env('CSE_PAGES', 2),
        'cse_num': get_int_env('CSE_NUM', 10),
    }

