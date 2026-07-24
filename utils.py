"""
utils.py
--------
Small, reusable helper functions used across GameVoicesBot:

- Logging configuration (console + rotating file handler).
- Markdown-V2 escaping for safe Telegram formatting.
- Text truncation.
- Best-effort translation into Uzbek via a LibreTranslate-compatible API,
  with a safe fallback to the original text if translation is unavailable.
"""

from __future__ import annotations

import logging
import logging.handlers
import re
import sys

import requests

import config


def setup_logging() -> logging.Logger:
    """Configure root logging for the whole application.

    Logs to stdout (so Render / any PaaS captures it in its log viewer) and
    to a rotating file under data/ for local persistence.
    """
    logger = logging.getLogger("gamevoices")
    logger.setLevel(config.LOG_LEVEL)

    if logger.handlers:
        # Avoid duplicate handlers if setup_logging() is called more than once.
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            config.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # If the filesystem is read-only (some PaaS setups), just skip file logging.
        logger.warning("Could not open log file for writing; continuing with console logging only.")

    # Quiet down noisy third-party loggers.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return logger


log = setup_logging()


_MDV2_SPECIAL_CHARS = r"_*[]()~`>#+-=|{}.!"


def escape_markdown_v2(text: str) -> str:
    """Escape a string for safe use inside Telegram MarkdownV2 messages."""
    if not text:
        return ""
    pattern = f"([{re.escape(_MDV2_SPECIAL_CHARS)}])"
    return re.sub(pattern, r"\\\1", text)


def truncate_text(text: str, max_length: int = 600) -> str:
    """Truncate text to max_length characters, cutting on a word boundary."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_length:
        return text
    cut = text[:max_length].rsplit(" ", 1)[0]
    return cut.rstrip(",.;: ") + "…"


def translate_to_uzbek(text: str) -> str:
    """Best-effort translation of `text` (assumed English) into Uzbek.

    If translation is disabled, the text is empty, or the translation
    service is unreachable/misconfigured, the original text is returned
    unchanged so the bot never crashes because of a translation failure.
    """
    if not text:
        return text

    if not config.TRANSLATE_ENABLED:
        return text

    payload = {
        "q": text,
        "source": "en",
        "target": "uz",
        "format": "text",
    }
    if config.LIBRETRANSLATE_API_KEY:
        payload["api_key"] = config.LIBRETRANSLATE_API_KEY

    try:
        response = requests.post(config.LIBRETRANSLATE_URL, json=payload, timeout=8)
        response.raise_for_status()
        data = response.json()
        translated = data.get("translatedText")
        if translated:
            return translated
        return text
    except Exception as exc:  # noqa: BLE001 - translation must never break posting
        log.warning("Translation failed, falling back to original text: %s", exc)
        return text


def chunk_list(items: list, size: int) -> list[list]:
    """Split a list into chunks of at most `size` items."""
    return [items[i : i + size] for i in range(0, len(items), size)]
