"""
main.py
-------
Entry point for GameVoicesBot.

Responsibilities:
- Build and configure the python-telegram-bot Application.
- Register admin command handlers: /start, /post, /history, /stats, /help.
- Wire up an APScheduler job that automatically posts fresh game news to the
  configured Telegram channel every POST_INTERVAL_HOURS (default: 6).
- Provide centralized error handling and logging.

Run with:  python main.py
"""

from __future__ import annotations

import asyncio
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

import config
import database
import history
from games import get_new_games_to_post, format_post_caption, GameFetchError
from scheduler import create_scheduler
from utils import log


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
def admin_only(handler: Callable):
    """Decorator that restricts a command handler to configured admin users."""

    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user or user.id not in config.ADMIN_IDS:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⛔️ Kechirasiz, bu buyruq faqat adminlar uchun mavjud."
                )
            log.warning(
                "Unauthorized command attempt by user_id=%s username=%s",
                getattr(user, "id", None),
                getattr(user, "username", None),
            )
            return
        return await handler(update, context, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Core posting logic (shared by the scheduler and the manual /post command)
# ---------------------------------------------------------------------------
async def post_new_games(context: ContextTypes.DEFAULT_TYPE, max_games: int = None, notify_chat_id: int = None) -> int:
    """Fetch fresh games, skip duplicates, and post new ones to the channel.

    Returns the number of games actually posted. Optionally sends a short
    summary to `notify_chat_id` (used by the manual /post command so the
    admin gets feedback in their private chat).
    """
    max_games = max_games or config.GAMES_PER_RUN
    bot = context.bot

    try:
        candidates = await asyncio.to_thread(get_new_games_to_post, max_games)
    except GameFetchError as exc:
        log.error("Game fetch failed: %s", exc)
        if notify_chat_id:
            await bot.send_message(
                chat_id=notify_chat_id,
                text=f"❌ O'yinlarni olishda xatolik yuz berdi: {exc}",
            )
        return 0

    posted_count = 0

    for game in candidates:
        if posted_count >= max_games:
            break

        is_dup = await asyncio.to_thread(database.is_duplicate, game["game_id"], game["platform"])
        if is_dup:
            continue

        caption = format_post_caption(game)

        try:
            if game.get("image_url"):
                await bot.send_photo(
                    chat_id=config.CHANNEL_ID,
                    photo=game["image_url"],
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                )
            else:
                await bot.send_message(
                    chat_id=config.CHANNEL_ID,
                    text=caption,
                    parse_mode=ParseMode.HTML,
                )
        except Exception as exc:  # noqa: BLE001 - one bad post must not stop the batch
            log.error("Failed to send post for game '%s': %s", game["title"], exc)
            continue

        await asyncio.to_thread(
            database.save_post,
            game["game_id"],
            game["title"],
            game["platform"],
            game.get("url"),
        )
        posted_count += 1
        # Small delay to stay well within Telegram rate limits when posting several games.
        await asyncio.sleep(2)

    log.info("Posting run complete: %s new game(s) posted.", posted_count)

    if notify_chat_id:
        if posted_count:
            await bot.send_message(
                chat_id=notify_chat_id,
                text=f"✅ {posted_count} ta yangi o'yin kanalga muvaffaqiyatli joylandi.",
            )
        else:
            await bot.send_message(
                chat_id=notify_chat_id,
                text="ℹ️ Yangi (hali post qilinmagan) o'yinlar topilmadi.",
            )

    return posted_count


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 Salom! Men <b>GameVoicesBot</b>man.\n\n"
        "Men PC, PlayStation, Xbox va Android platformalari uchun eng so'nggi "
        "o'yin yangiliklarini avtomatik ravishda kanalga joylashtiraman.\n\n"
        "Mavjud buyruqlar ro'yxati uchun /help buyrug'ini yuboring."
    )
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🧭 <b>Buyruqlar ro'yxati:</b>\n\n"
        "/start — Botni ishga tushirish va tanishtiruv\n"
        "/post — Yangi o'yinlarni qo'lda qidirib, kanalga joylash (faqat admin)\n"
        "/history — Oxirgi joylangan postlar tarixi (faqat admin)\n"
        "/stats — Bot statistikasi (faqat admin)\n"
        "/help — Ushbu yordam xabari\n\n"
        f"⏱ Avtomatik post har {config.POST_INTERVAL_HOURS} soatda amalga oshiriladi."
    )
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@admin_only
async def cmd_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("🔎 Yangi o'yinlar qidirilmoqda, iltimos kuting...")
    await post_new_games(context, notify_chat_id=update.effective_chat.id)


@admin_only
async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = await asyncio.to_thread(history.format_history_message, 10)
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


@admin_only
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = await asyncio.to_thread(history.format_stats_message)
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Unhandled exception while processing update %s", update, exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Kutilmagan xatolik yuz berdi. Muammo davom etsa, iltimos keyinroq qayta urinib ko'ring."
            )
        except Exception:  # noqa: BLE001 - best effort only
            pass


# ---------------------------------------------------------------------------
# Application lifecycle
# ---------------------------------------------------------------------------
async def on_startup(application: Application) -> None:
    """Runs once, inside the bot's event loop, right before polling starts."""

    async def bound_scheduled_job():
        await post_new_games(application.bot_data["fresh_context"])

    # Build a lightweight context-like object exposing `.bot` for post_new_games.
    class _MinimalContext:
        def __init__(self, bot):
            self.bot = bot

    application.bot_data["fresh_context"] = _MinimalContext(application.bot)

    sched = create_scheduler(bound_scheduled_job, hours=config.POST_INTERVAL_HOURS)
    sched.start()
    application.bot_data["scheduler"] = sched
    log.info("APScheduler started; automatic posting is active.")


async def on_shutdown(application: Application) -> None:
    sched = application.bot_data.get("scheduler")
    if sched:
        sched.shutdown(wait=False)
        log.info("APScheduler stopped.")


def main() -> None:
    problems = config.validate_config()
    if problems:
        for problem in problems:
            log.warning("Configuration issue: %s", problem)
        if not config.BOT_TOKEN:
            log.critical("BOT_TOKEN is required to start the bot. Exiting.")
            return

    database.init_db()

    application = (
        ApplicationBuilder()
        .token(config.BOT_TOKEN)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("post", cmd_post))
    application.add_handler(CommandHandler("history", cmd_history))
    application.add_handler(CommandHandler("stats", cmd_stats))

    application.add_error_handler(error_handler)

    log.info("GameVoicesBot starting (polling mode)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
