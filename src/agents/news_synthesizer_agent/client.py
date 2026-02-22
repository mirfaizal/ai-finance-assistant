"""OpenAI client initialisation for the News Synthesizer Agent."""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_CONFIG_PATH = Path(__file__).resolve().parents[4] / "config.yaml"


def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


_config = _load_config()
_openai_cfg = _config.get("openai", {})

MODEL: str = _openai_cfg.get("model", "gpt-4o-mini")
TEMPERATURE: float = float(_openai_cfg.get("temperature", 0.3))


def get_client() -> OpenAI:
    """Return an initialised OpenAI client."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. "
            "Add it to your environment or to a .env file in the project root."
        )
    return OpenAI(api_key=api_key)
