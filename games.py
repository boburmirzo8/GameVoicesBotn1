"""
games.py
--------
Fetches game information (title, description, cover image, release date,
platforms) from the RAWG.io API (https://rawg.io/apidocs) and formats it
into ready-to-send Telegram posts written in Uzbek.

RAWG is used because it is free, well documented, covers PC, PlayStation,
Xbox and Android/mobile titles, and returns high quality cover images and
descriptions without requiring scraping.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import requests

import config
from utils import log, translate_to_uzbek, truncate_text


class GameFetchError(Exception):
    """Raised when the RAWG API cannot be reached or returns an error."""


def _rawg_get(path: str, params: dict) -> dict:
    """Perform a GET request against the RAWG API and return parsed JSON."""
    if not config.RAWG_API_KEY:
        raise GameFetchError("RAWG_API_KEY is not configured.")

    url = f"{config.RAWG_BASE_URL}{path}"
    params = {**params, "key": config.RAWG_API_KEY}

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise GameFetchError(f"RAWG API request failed: {exc}") from exc


def fetch_recent_games(platform_name: str, days_back: int = 3, page_size: int = 10) -> list[dict]:
    """Return a list of recently released/updated games for a given platform group.

    `platform_name` must be one of the keys in config.PLATFORM_RAWG_IDS
    (PC, PlayStation, Xbox, Android).
    """
    platform_ids = config.PLATFORM_RAWG_IDS.get(platform_name)
    if not platform_ids:
        raise ValueError(f"Unknown platform: {platform_name}")

    date_to = datetime.utcnow().date()
    date_from = date_to - timedelta(days=days_back)

    params = {
        "platforms": ",".join(str(pid) for pid in platform_ids),
        "dates": f"{date_from.isoformat()},{date_to.isoformat()}",
        "ordering": "-added",
        "page_size": page_size,
    }

    data = _rawg_get("/games", params)
    return data.get("results", [])


def fetch_game_description(game_id: int) -> str:
    """Fetch the plain-text description for a specific game by RAWG ID."""
    data = _rawg_get(f"/games/{game_id}", {})
    description = data.get("description_raw", "") or ""
    return description.strip()


def build_game_post(raw_game: dict, platform_name: str) -> Optional[dict]:
    """Turn a raw RAWG game dict into a structured, ready-to-post payload.

    Returns None if essential data (title) is missing.
    """
    game_id = raw_game.get("id")
    title = raw_game.get("name")
    if not game_id or not title:
        return None

    image_url = raw_game.get("background_image")
    release_date = raw_game.get("released") or "Noma'lum"
    rating = raw_game.get("rating")
    metacritic = raw_game.get("metacritic")

    try:
        description_en = fetch_game_description(game_id)
    except GameFetchError as exc:
        log.warning("Could not fetch description for game %s: %s", game_id, exc)
        description_en = raw_game.get("description_raw", "") or ""

    description_en = truncate_text(description_en, 500)
    description_uz = translate_to_uzbek(description_en) if description_en else (
        "Ushbu o'yin haqida qo'shimcha ma'lumot topilmadi."
    )

    rawg_url = raw_game.get("slug")
    game_url = f"https://rawg.io/games/{rawg_url}" if rawg_url else None

    return {
        "game_id": str(game_id),
        "title": title,
        "platform": platform_name,
        "image_url": image_url,
        "release_date": release_date,
        "rating": rating,
        "metacritic": metacritic,
        "description_uz": description_uz,
        "url": game_url,
    }


def format_post_caption(game: dict) -> str:
    """Format a game payload into a Telegram-ready caption written in Uzbek.

    Uses plain formatting compatible with Telegram's default HTML parse mode.
    """
    platform_label = config.PLATFORM_LABELS_UZ.get(game["platform"], game["platform"])
    title = game["title"]

    lines = [
        f"🎮 <b>{title}</b>",
        "",
        f"📅 <b>Chiqarilgan sana:</b> {game['release_date']}",
        f"🕹 <b>Platforma:</b> {platform_label}",
    ]

    if game.get("rating"):
        lines.append(f"⭐️ <b>Reyting:</b> {game['rating']}/5")
    if game.get("metacritic"):
        lines.append(f"📊 <b>Metacritic:</b> {game['metacritic']}/100")

    lines.append("")
    lines.append(f"📝 <b>Tavsif:</b>\n{game['description_uz']}")

    if game.get("url"):
        lines.append("")
        lines.append(f'🔗 <a href="{game["url"]}">Batafsil ma\'lumot</a>')

    lines.append("")
    lines.append("📢 @GameVoicesBot orqali yangiliklardan xabardor bo'ling!")

    return "\n".join(lines)


def get_new_games_to_post(max_games: int = 4) -> list[dict]:
    """Collect fresh, not-yet-posted games across all supported platforms.

    This is the main entry point used by both the scheduler and the manual
    /post command. Duplicate filtering against the database happens in the
    caller (main.py) right before sending, to keep this module free of any
    database dependency.
    """
    all_games: list[dict] = []

    for platform_name in config.PLATFORM_RAWG_IDS:
        try:
            raw_games = fetch_recent_games(platform_name, days_back=config.GAMES_LOOKBACK_DAYS)
        except GameFetchError as exc:
            log.error("Failed to fetch games for platform %s: %s", platform_name, exc)
            continue

        for raw_game in raw_games:
            post = build_game_post(raw_game, platform_name)
            if post:
                all_games.append(post)

        if len(all_games) >= max_games * 2:
            # Gathered plenty of candidates already; stop early to save API calls.
            break

    return all_games
