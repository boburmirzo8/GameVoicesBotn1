"""
config.py
---------
Centralized configuration for GameVoicesBot.

All configuration values are loaded from environment variables so the bot
can be safely deployed on platforms like Render without hardcoding secrets.

Uses python-dotenv locally (loads a .env file if present). On Render (or any
other host) real environment variables are injected directly and .env is
simply ignored if it doesn't exist.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file if present (does nothing in production if the file is absent)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _get_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_int_list(name: str) -> list[int]:
    raw = os.getenv(name, "")
    result = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                result.append(int(part))
            except ValueError:
                continue
    return result


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")  # e.g. @gamevoices or -1001234567890
ADMIN_IDS: list[int] = _get_int_list("ADMIN_IDS")  # comma separated Telegram user IDs

# ---------------------------------------------------------------------------
# Game data provider (RAWG.io - free video game database API)
# https://rawg.io/apidocs
# ---------------------------------------------------------------------------
RAWG_API_KEY: str = os.getenv("RAWG_API_KEY", "")
RAWG_BASE_URL: str = "https://api.rawg.io/api"

# ---------------------------------------------------------------------------
# Translation (optional - LibreTranslate compatible endpoint)
# If unreachable or not configured, the bot gracefully falls back to the
# original (usually English) text instead of failing the whole post.
# ---------------------------------------------------------------------------
TRANSLATE_ENABLED: bool = _get_bool("TRANSLATE_ENABLED", True)
LIBRETRANSLATE_URL: str = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.com/translate")
LIBRETRANSLATE_API_KEY: str = os.getenv("LIBRETRANSLATE_API_KEY", "")

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
POST_INTERVAL_HOURS: int = _get_int("POST_INTERVAL_HOURS", 6)
GAMES_LOOKBACK_DAYS: int = _get_int("GAMES_LOOKBACK_DAYS", 3)
GAMES_PER_RUN: int = _get_int("GAMES_PER_RUN", 4)  # max games posted per scheduled run
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Tashkent")

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
DATA_DIR: Path = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH: str = str(DATA_DIR / "gamevoices.db")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = str(DATA_DIR / "gamevoices.log")

# ---------------------------------------------------------------------------
# Platforms supported by the bot, mapped to RAWG platform IDs.
# See https://api.rawg.io/api/platforms for the full list of IDs.
# ---------------------------------------------------------------------------
PLATFORM_RAWG_IDS: dict[str, list[int]] = {
    "PC": [4],
    "PlayStation": [187, 18, 16],       # PS5, PS4, PS3
    "Xbox": [186, 1, 14],               # Xbox Series S/X, Xbox One, Xbox 360
    "Android": [21],
}

# Human-friendly Uzbek labels for each platform, used in post formatting.
PLATFORM_LABELS_UZ: dict[str, str] = {
    "PC": "🖥 PC",
    "PlayStation": "🎮 PlayStation",
    "Xbox": "🟢 Xbox",
    "Android": "📱 Android",
}


def validate_config() -> list[str]:
    """Return a list of human-readable configuration problems (empty if OK)."""
    problems = []
    if not BOT_TOKEN:
        problems.append("BOT_TOKEN is not set.")
    if not CHANNEL_ID:
        problems.append("CHANNEL_ID is not set.")
    if not ADMIN_IDS:
        problems.append("ADMIN_IDS is not set (no admins configured).")
    if not RAWG_API_KEY:
        problems.append("RAWG_API_KEY is not set (game data fetching will fail).")
    return problems
