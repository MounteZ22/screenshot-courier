"""APScheduler-based screenshot scheduler."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


def create_scheduler(interval_minutes: int, job_func) -> BackgroundScheduler:
    """Create and start a background scheduler for periodic screenshots.

    Args:
        interval_minutes: Minutes between screenshots.
        job_func: Callable to invoke on each tick.

    Returns:
        The started scheduler instance.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        job_func,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="screenshot_job",
        name="定时截图发送",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    logger.info("Scheduler started: interval=%d min", interval_minutes)
    return scheduler


def update_scheduler_interval(scheduler: BackgroundScheduler, interval_minutes: int, job_func):
    """Reschedule the job with a new interval."""
    scheduler.remove_job("screenshot_job")
    scheduler.add_job(
        job_func,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="screenshot_job",
        name="定时截图发送",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    logger.info("Scheduler rescheduled: interval=%d min", interval_minutes)
