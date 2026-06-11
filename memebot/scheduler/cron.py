"""Batch scheduler using APScheduler."""

from __future__ import annotations

import logging
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from memebot.config import Settings
from memebot.generator.pipeline import generate_batch

logger = logging.getLogger(__name__)


def run_scheduled_batch(settings: Settings) -> None:
    logger.info("Running scheduled meme batch (size=%d)", settings.batch_size)
    memes = generate_batch(settings)
    logger.info("Scheduled run complete: %d memes", len(memes))


def start_scheduler(settings: Settings, cron: str = "0 9 * * *") -> None:
    """Block and run meme generation on a cron schedule."""
    scheduler = BlockingScheduler(timezone=settings.scheduler_timezone)
    parts = cron.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (need 5 fields): {cron}")

    minute, hour, day, month, day_of_week = parts
    trigger = CronTrigger(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        timezone=settings.scheduler_timezone,
    )

    scheduler.add_job(
        run_scheduled_batch,
        trigger=trigger,
        args=[settings],
        id="memebot_daily_batch",
        replace_existing=True,
    )

    def _shutdown(signum: int, frame: object) -> None:
        logger.info("Shutting down scheduler (signal %s)", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown)

    logger.info("Scheduler started — cron=%r timezone=%s", cron, settings.scheduler_timezone)
    logger.info("Press Ctrl+C to stop")
    scheduler.start()
