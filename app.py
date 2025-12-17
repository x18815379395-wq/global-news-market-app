"""Main application module for HorizonScanner."""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask

try:
    from flask_cors import CORS
except ImportError:  # pragma: no cover
    CORS = None  # type: ignore

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from app_utils import SmartCache, get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/horizonscanner.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("horizonscanner")

# Load environment variables if available
if load_dotenv:
    load_dotenv(os.getenv("EARSOFFORTUNE_DOTENV", ".env"))

# Check essential dependencies
required_dependencies = [
    ("requests", "HTTP requests"),
    ("feedparser", "RSS parsing"),
    ("news", "News pipeline"),
]

missing_dependencies = []
for dep, description in required_dependencies:
    try:
        __import__(dep)
        logger.info(f"OK: {dep} (for {description}) is installed")
    except ImportError:
        logger.error(f"ERROR: {dep} (for {description}) is missing")
        missing_dependencies.append(dep)

if missing_dependencies:
    logger.warning(f"Missing dependencies: {', '.join(missing_dependencies)}")
    logger.warning("Some functionality may be limited. Please install missing dependencies.")

# Constants
PROJECT_ROOT = Path(__file__).resolve().parent
SCRAPER_TOOL_ROOT = PROJECT_ROOT / "no-api-news-scraper" / "crawler"
CACHE_TTL_SECONDS = 90
DEFAULT_PORT = 5000
DEFAULT_HOST = "127.0.0.1"
DEFAULT_DEBUG = False

# Initialize Flask app
app = Flask(__name__, template_folder='templates')
if CORS:
    CORS(app)

# Initialize cache
global_cache = SmartCache(ttl_seconds=CACHE_TTL_SECONDS)

# Initialize no-api doctor if available
_no_api_doctor = None
if SCRAPER_TOOL_ROOT.exists():
    scraper_path = str(SCRAPER_TOOL_ROOT)
    if scraper_path not in sys.path:
        sys.path.insert(0, scraper_path)
    try:
        from tools import doctor as _doctor_module  # type: ignore
        _no_api_doctor = _doctor_module
    except ImportError as exc:  # pragma: no cover - optional tool
        logger.warning("Failed to import no-api doctor module: %s", exc)
    except Exception as exc:  # pragma: no cover - optional tool
        logger.warning("Failed to load no-api doctor due to unexpected error: %s", exc)

# Load API keys
DEEPSEEK_API_KEY = get_env("DEEPSEEK_API_KEY", required=False)

# LegacyNewsManager for backward compatibility
class LegacyNewsManager:
    """Backwards-compatible shim exposing the legacy news_manager API surface."""

    def __init__(self, cache: SmartCache) -> None:
        self._cache = cache

    def get_health_snapshot(self, force_refresh: bool = False) -> dict:
        """Get health snapshot."""
        cache_key = "legacy:news_health"
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached:
                return cached

        from news import get_pipeline_status
        
        def _get_news_health(status_payload):
            info = {}
            x_ready = False
            for entry in status_payload.get("pipeline", {}).get("health", []):
                name = entry.get("name", "unknown")
                info[name] = {
                    "healthy": entry.get("healthy"),
                    "last_error": entry.get("last_error"),
                    "last_success": entry.get("last_success"),
                    "items_last_fetch": entry.get("items_last_fetch"),
                    "latency_ms": entry.get("latency_ms"),
                    "extra": entry.get("extra"),
                }
            return info
        
        try:
            raw_health = _get_news_health(get_pipeline_status())
            shaped = self._group_health(raw_health)
            self._cache.set(cache_key, shaped)
            return shaped
        except Exception as exc:
            logger.error("Failed to get health snapshot: %s", exc)
            return {"error": str(exc)}

    def _group_health(self, entries: dict) -> dict:
        """Group health entries by type."""
        grouped = {
            "rss": {},
            "truth_social": {},
            "twitter": {},
            "other": {},
        }
        total_sources = 0
        healthy_sources = 0
        
        for name, payload in entries.items():
            bucket = self._bucket_for(name)
            entry = {
                "healthy": payload.get("healthy"),
                "items_last_fetch": payload.get("items_last_fetch"),
                "last_success": payload.get("last_success"),
                "last_error": payload.get("last_error"),
                "latency_ms": payload.get("latency_ms"),
            }
            grouped[bucket][name] = entry
            total_sources += 1
            if entry["healthy"]:
                healthy_sources += 1

        summary = {
            "rss": grouped["rss"],
            "truth_social": grouped["truth_social"],
            "twitter": grouped["twitter"],
            "other": grouped["other"],
            "generated_at": self._get_current_timestamp(),
            "sources_total": total_sources,
            "healthy_sources": healthy_sources,
        }
        if not entries:
            summary["status"] = "no_adapters"
        return summary

    @staticmethod
    def _bucket_for(name: str) -> str:
        """Determine bucket for adapter name."""
        lowered = name.lower()
        if lowered.startswith(("x:", "twitter:")):
            return "twitter"
        if lowered.startswith(("truth:", "truthsocial:")):
            return "truth_social"
        if ":" in lowered:
            return "other"
        return "rss"

    def _get_current_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

# Initialize legacy news manager
news_manager = LegacyNewsManager(global_cache)

# Register API routes
from api_routes import register_routes
register_routes(app, global_cache, _no_api_doctor, DEEPSEEK_API_KEY, news_manager)

# Data processing functions for backward compatibility
def get_news_safe():
    """Backward compatible function to get news."""
    from data_processing import get_news_safe as _get_news_safe
    return _get_news_safe(global_cache)

def get_news_safe_original():
    """Backward compatible function to get original news."""
    from data_processing import get_news_safe_original as _get_news_safe_original
    return _get_news_safe_original()

def get_mock_horizon_scanner_data():
    """Backward compatible function to get real data instead of mock data."""
    from data_processing import (
        build_smart_hint,
        compute_risk_metrics,
        get_news_safe,
        summarise_markets,
        transform_articles_to_signals,
    )
    articles = get_news_safe(global_cache)
    signals = transform_articles_to_signals(articles)
    risk = compute_risk_metrics(signals)
    smart_hint = build_smart_hint(signals, risk)
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signals": signals,
        "summary": summarise_markets(signals),
        "risk_metrics": risk,
        "smart_hint": smart_hint,
        "total_signals": len(signals),
        "status": "success",
    }

def get_no_api_health_snapshot(force_refresh: bool = False):
    """Backward compatible function to get no API health snapshot."""
    cache_key = "no_api:health"
    if not force_refresh:
        cached = global_cache.get(cache_key)
        if cached:
            return cached
    
    if not _no_api_doctor:
        return None
        
    try:
        status = _no_api_doctor.collect_status()
        global_cache.set(cache_key, status)
        return status
    except Exception as exc:  # pragma: no cover - network dependent
        logger.error("No-API doctor failed: %s", exc)
        return {"error": str(exc)}

# Export names for backward compatibility
__all__ = [
    "app",
    "get_news_safe",
    "get_news_safe_original",
    "get_mock_horizon_scanner_data",
    "get_no_api_health_snapshot",
    "news_manager",
]
