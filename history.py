"""
history.py
----------
Formats stored post history and statistics into Telegram-ready messages for
the /history and /stats admin commands.
"""

from __future__ import annotations

from datetime import datetime

import config
import database


def _format_datetime(iso_string: str) -> str:
    """Convert an ISO-8601 UTC timestamp into a readable Uzbek-friendly string."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, TypeError):
        return iso_string or "Noma'lum"


def format_history_message(limit: int = 10) -> str:
    """Build the message shown for the /history command."""
    rows = database.get_history(limit=limit)

    if not rows:
        return "🗂 Hozircha hech qanday post tarixi mavjud emas."

    lines = [f"🗂 <b>Oxirgi {len(rows)} ta post:</b>", ""]
    for row in rows:
        platform_label = config.PLATFORM_LABELS_UZ.get(row["platform"], row["platform"])
        posted_at = _format_datetime(row["posted_at"])
        title = row["title"]
        url = row["url"]

        line = f"• <b>{title}</b> — {platform_label}\n   🕒 {posted_at}"
        if url:
            line += f"\n   🔗 <a href=\"{url}\">Havola</a>"
        lines.append(line)

    return "\n".join(lines)


def format_stats_message() -> str:
    """Build the message shown for the /stats command."""
    stats = database.get_stats()
    total = stats["total"]
    by_platform = stats["by_platform"]
    last_post_at = stats["last_post_at"]

    lines = [
        "📊 <b>GameVoicesBot statistikasi</b>",
        "",
        f"📦 <b>Jami e'lon qilingan o'yinlar:</b> {total}",
    ]

    if by_platform:
        lines.append("")
        lines.append("🕹 <b>Platformalar bo'yicha:</b>")
        for platform, count in by_platform.items():
            label = config.PLATFORM_LABELS_UZ.get(platform, platform)
            lines.append(f"  • {label}: {count}")

    lines.append("")
    lines.append(f"⏱ <b>Oxirgi post vaqti:</b> {_format_datetime(last_post_at) if last_post_at else 'Hozircha yo\u2018q'}")
    lines.append(f"⚙️ <b>Avtomatik post oralig\u2018i:</b> {config.POST_INTERVAL_HOURS} soat")

    return "\n".join(lines)
