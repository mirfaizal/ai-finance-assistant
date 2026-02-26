"""OpenAI client for the Memory Synthesizer Agent."""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_CONFIG_PATH = Path(__file__).resolve().parents[4] / "config.yaml"


def _load_config() -> dict:
    """Load the project-level config.yaml and return it as a dict (empty dict if missing)."""
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    return {}


_cfg = _load_config()
MODEL = _cfg.get("llm", {}).get("model", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
TEMPERATURE = float(_cfg.get("llm", {}).get("temperature", 0.3))


def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)
