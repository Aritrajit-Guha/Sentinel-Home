from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import settings
from app.scheduling.tasks import check_all_households

scheduler = BackgroundScheduler()


def _new_scheduler() -> BackgroundScheduler:
    return BackgroundScheduler()


def start_scheduler() -> bool:
    """Start one monitoring job, returning whether startup occurred."""
    global scheduler

    if scheduler.running:
        return False
    if settings.MONITOR_INTERVAL_MINUTES < 1:
        raise ValueError("MONITOR_INTERVAL_MINUTES must be at least 1")

    scheduler.add_job(
        check_all_households,
        "interval",
        minutes=settings.MONITOR_INTERVAL_MINUTES,
        id="household-monitoring",
        replace_existing=True,
    )
    scheduler.start()
    return True


def stop_scheduler() -> bool:
    global scheduler

    if not scheduler.running:
        return False
    scheduler.shutdown(wait=False)
    # APScheduler instances cannot be started again after shutdown.
    scheduler = _new_scheduler()
    return True


def scheduler_status() -> dict:
    job = scheduler.get_job("household-monitoring")
    return {
        "enabled": settings.ENABLE_SCHEDULER,
        "running": scheduler.running,
        "interval_minutes": settings.MONITOR_INTERVAL_MINUTES,
        "next_run_at": job.next_run_time.isoformat() if job and job.next_run_time else None,
    }
