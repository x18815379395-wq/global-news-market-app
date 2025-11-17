"""
Load `HorizonScanner/news_sources.yaml` with optional env overrides.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:  # pragma: no cover - dependency missing in some envs
    yaml = None


def load_sources_config() -> Dict[str, Any]:
    config_path = Path("HorizonScanner") / "news_sources.yaml"
    if not config_path.exists():
        logger.warning("news_sources.yaml not found at %s", config_path)
        return {}
    raw = config_path.read_text(encoding="utf-8")
    data: Dict[str, Any]
    if yaml:
        data = yaml.safe_load(raw) or {}
    else:
        logger.error("PyYAML not available; attempting JSON parsing fallback.")
        data = json.loads(raw)
    return _expand_env(data)


def _expand_env(data: Dict[str, Any]) -> Dict[str, Any]:
    def replace(value: Any) -> Any:
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_key = value[2:-1]
            return os.getenv(env_key, "")
        if isinstance(value, dict):
            return {k: replace(v) for k, v in value.items()}
        if isinstance(value, list):
            return [replace(item) for item in value]
        return value

    return replace(data)  # type: ignore[return-value]
