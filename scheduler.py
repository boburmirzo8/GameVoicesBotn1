"""
scheduler.py
------------
Sets up an APScheduler AsyncIOScheduler that periodically triggers the
game-posting job (every POST_INTERVAL_HOURS, default 6).

The scheduler runs inside the same asyncio event loop as the Telegram bot
(python-telegram-bot's Application), so the scheduled job is an async
function and APScheduler's AsyncIOScheduler natively awaits it.
"""

from __future__ import annotations

from typing import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
from utils import log

JobFunc = Callable[[], Awaitable[None]]


def create_scheduler(job_func: JobFunc, hours: int = None) -> AsyncIOScheduler:
    """Create (but do not start) an AsyncIOScheduler that runs `job_func`
    every `hours` hours. The scheduler must be started with `.start()`
    from within a running asyncio event loop.
    """
    hours = hours or config.POST_INTERVAL_HOURS

    scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)
    scheduler.add_job(
        job_func,
        trigger=IntervalTrigger(hours=hours),
        id="auto_post_games",
        name="Automatic game news posting",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
        misfire_grace_time=3600,
    )
    log.info("Scheduler configured: job will run every %s hour(s).", hours)
    return scheduler
