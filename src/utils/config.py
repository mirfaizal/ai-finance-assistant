"""
Centralized configuration loader for the AI Finance Assistant.
Reads from config.yaml and exposes configurable constants.
"""
from pathlib import Path
import yaml

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"

def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

_cfg = _load_config()
_api_endpoints = _cfg.get("api_endpoints", {})

FINNHUB_BASE_URL = _api_endpoints.get("finnhub", {}).get("base_url", "https://finnhub.io/api/v1")

YAHOO_RSS_FEEDS = _api_endpoints.get("yahoo_finance", {
    "top_stories": "https://finance.yahoo.com/rss/topfinstories",
    "markets": "https://finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US",
    "technology": "https://finance.yahoo.com/rss/2.0/headline?s=%5ENDX&region=US&lang=en-US",
    "crypto": "https://finance.yahoo.com/rss/2.0/headline?s=BTC-USD&region=US&lang=en-US",
    "economy": "https://finance.yahoo.com/rss/2.0/headline?s=%5ETNX&region=US&lang=en-US",
})
