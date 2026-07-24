"""
database.py
-----------
SQLite persistence layer for GameVoicesBot.

Responsible for:
- Creating the schema on first run.
- Preventing duplicate posts (a game is only ever posted once per platform).
- Storing post history for the /history and /stats admin commands.

All functions are synchronous (sqlite3 is fine for this workload); they are
called from async handlers via `asyncio.to_thread` where appropriate to
avoid blocking the event loop.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

import config
from utils import log

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    title TEXT NOT NULL,
    platform TEXT NOT NULL,
    url TEXT,
    posted_at TEXT NOT NULL,
    UNIQUE(game_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_posts_game_platform ON posts(game_id, platform);
CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at);
"""


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection with sane defaults, always closed afterwards."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables/indexes if they do not already exist."""
    with get_connection() as conn:
        conn.executescript(SCHEMA)
    log.info("Database initialized at %s", config.DATABASE_PATH)


def is_duplicate(game_id: str, platform: str) -> bool:
    """Return True if this game has already been posted for this platform."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM posts WHERE game_id = ? AND platform = ? LIMIT 1",
            (game_id, platform),
        ).fetchone()
        return row is not None


def save_post(game_id: str, title: str, platform: str, url: Optional[str] = None) -> None:
    """Record a successfully posted game so it is never posted again."""
    posted_at = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO posts (game_id, title, platform, url, posted_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (game_id, title, platform, url, posted_at),
        )
    log.info("Saved post record: [%s] %s (game_id=%s)", platform, title, game_id)


def get_history(limit: int = 10) -> list[sqlite3.Row]:
    """Return the most recent `limit` posts, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM posts ORDER BY posted_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return rows


def get_stats() -> dict:
    """Return aggregate statistics: total posts and a per-platform breakdown."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM posts").fetchone()["c"]
        by_platform_rows = conn.execute(
            "SELECT platform, COUNT(*) AS c FROM posts GROUP BY platform ORDER BY c DESC"
        ).fetchall()
        last_post_row = conn.execute(
            "SELECT posted_at FROM posts ORDER BY posted_at DESC LIMIT 1"
        ).fetchone()

    by_platform = {row["platform"]: row["c"] for row in by_platform_rows}
    last_post_at = last_post_row["posted_at"] if last_post_row else None

    return {
        "total": total,
        "by_platform": by_platform,
        "last_post_at": last_post_at,
    }
