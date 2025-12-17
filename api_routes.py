"""API routes for HorizonScanner."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flask import jsonify, request

from data_processing import (
    build_backtest_report,
    build_smart_hint,
    compute_risk_metrics,
    get_news_safe,
    transform_articles_to_signals,
)
from news import SETTINGS, get_pipeline_status

logger = logging.getLogger("horizonscanner")


def register_routes(app, cache, no_api_doctor, deepseek_api_key, legacy_news_manager):
    """Register all API routes with the Flask app.
    
    Args:
        app: Flask app instance.
        cache: SmartCache instance.
        no_api_doctor: No-API doctor module.
        deepseek_api_key: DeepSeek API key.
        legacy_news_manager: LegacyNewsManager instance.
    """
    
    @app.context_processor
    def inject_globals():
        """Inject global variables into templates."""
        return {
            "build_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
    
    @app.route("/")
    def index():
        """Index page route."""
        from flask import render_template
        return render_template("index.html")
    
    @app.route("/api/horizon-scanner-data")
    def api_horizon_data():
        """API endpoint for horizon scanner data."""
        logger.info("Received request for horizon scanner data")
        try:
            articles = get_news_safe(cache)
            logger.debug(f"Retrieved {len(articles)} articles from news pipeline")
            
            signals = transform_articles_to_signals(articles)
            logger.debug(f"Transformed articles into {len(signals)} signals")
            
            risk = compute_risk_metrics(signals)
            logger.debug(f"Computed risk metrics: {risk}")
            
            smart_hint = build_smart_hint(signals, risk)
            logger.debug(f"Built smart hint: {smart_hint['title']}")
            
            from data_processing import summarise_markets
            summary = summarise_markets(signals)
            logger.debug(f"Generated market summary: {summary['headline']}")
            
            payload = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "signals": signals,
                "summary": summary,
                "risk_metrics": risk,
                "smart_hint": smart_hint,
                "total_signals": len(signals),
                "status": "success",
            }
            
            logger.info(f"Successfully generated horizon scanner data with {len(signals)} signals")
            return jsonify(payload)
        except Exception as exc:  # pragma: no cover
            logger.error("API horizon data failed: %s", exc, exc_info=True)
            return jsonify({"status": "error", "error": "Failed to load signals"}), 500
    
    @app.route("/api/signals/backtest", methods=["POST"])
    def api_signals_backtest():
        """API endpoint for backtest reports."""
        payload = request.get_json(silent=True) or {}
        market = payload.get("market") or "GLOBAL"
        window = payload.get("window") or "T+3"
        
        logger.info(f"Received backtest request for market: {market}, window: {window}")

        try:
            report = build_backtest_report(market, window, cache)
            logger.info(f"Successfully generated backtest report for {market} with window {window}")
            logger.debug(f"Backtest report headline: {report['headline']}")
            return jsonify({"status": "success", "report": report})
        except Exception as exc:  # pragma: no cover
            logger.error(f"Backtest generation failed for market {market}, window {window}: %s", exc, exc_info=True)
            return jsonify({"status": "error", "error": "无法生成回测报告"}), 500
    
    @app.route("/api/system-health")
    def api_system_health():
        """API endpoint for system health status."""
        logger.info("Received request for system health status")
        try:
            def get_no_api_health_snapshot(force_refresh: bool = False) -> Optional[Dict[str, Any]]:
                """Expose doctor.py health snapshot for integration with the UI."""
                if not no_api_doctor:
                    return None

                cache_key = "no_api:health"
                if not force_refresh:
                    cached = cache.get(cache_key)
                    if cached:
                        return cached
                try:
                    status = no_api_doctor.collect_status()
                    cache.set(cache_key, status)
                    return status
                except Exception as exc:  # pragma: no cover - optional tool
                    logger.warning("No-API doctor failed: %s", exc)
                    return {"error": str(exc)}
            
            def _get_news_health(status_payload: Optional[Dict[str, Any]] = None):
                if status_payload is None:
                    try:
                        status_payload = get_pipeline_status()
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.error("Health snapshot failed: %s", exc)
                        return {}, False, {}
                info: Dict[str, Dict[str, Any]] = {}
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
                    lowered = str(name).lower()
                    if "twitter" in lowered or lowered.startswith("x"):
                        x_ready = x_ready or bool(entry.get("healthy"))
                return info, x_ready, status_payload
            
            cached = bool(cache.get("news:enhanced"))
            news_health, x_ready, pipeline_status = _get_news_health()
            no_api_health = get_no_api_health_snapshot()
            env_block = {
                "DEEPSEEK": bool(deepseek_api_key),
                "X_PLAYWRIGHT": x_ready,
            }
            if isinstance(no_api_health, dict):
                env_block["NO_API_TWITTER_READY"] = no_api_health.get("twitter_ready")

            return jsonify(
                {
                    "status": "ok",
                    "cache_warm": cached,
                    "env": env_block,
                    "news_health": news_health,
                    "pipeline_status": pipeline_status,
                    "no_api_health": no_api_health,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as exc:
            logger.error("System health check failed: %s", exc, exc_info=True)
            return jsonify({
                "status": "error",
                "error": "Failed to retrieve system health status",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500
