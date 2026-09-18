"""Configuration management for OllaCode."""
import os
from pathlib import Path
from platformdirs import user_config_dir

APP_NAME = "ollacode"

def get_config_dir() -> Path:
    """Return OS-appropriate config directory."""
    env_dir = os.environ.get("OLLACODE_CONFIG_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(user_config_dir(APP_NAME))

def get_ollama_url() -> str:
    """Return a normalized Ollama server URL from environment or default."""
    url = (
        os.environ.get("OLLAMA_BASE_URL")
        or os.environ.get("OLLAMA_HOST")
        or "http://localhost:11434"
    ).strip()
    if not url:
        return "http://localhost:11434"
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return url.rstrip("/")

DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_OLLAMA_URL = get_ollama_url()
CONFIG_DIR = get_config_dir()
HISTORY_FILE = CONFIG_DIR / "history.txt"
CONFIG_FILE = CONFIG_DIR / "config.json"
