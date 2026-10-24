from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import settings
from app.scheduling.tasks import check_all_households, check_pending_alerts

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
    scheduler.add_job(
        check_pending_alerts,
        "interval",
        minutes=1,
        id="alert-delivery-and-escalation",
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
    delivery_job = scheduler.get_job("alert-delivery-and-escalation")
    from app.core.store import monitoring_runs
    live_runs = [run for run in monitoring_runs.values() if run.get("source") == "live"]
    completed = [run for run in live_runs if run.get("completed_at")]
    last_completed = max(completed, key=lambda run: run.get("completed_at", "")) if completed else None
    running = [run for run in live_runs if run.get("status") == "running"]
    return {
        "enabled": settings.ENABLE_SCHEDULER,
        "running": scheduler.running,
        "interval_minutes": settings.MONITOR_INTERVAL_MINUTES,
        "next_run_at": job.next_run_time.isoformat() if job and job.next_run_time else None,
        "next_delivery_run_at": (
            delivery_job.next_run_time.isoformat()
            if delivery_job and delivery_job.next_run_time else None
        ),
        "last_heartbeat_at": max((run.get("started_at") for run in live_runs if run.get("started_at")), default=None),
        "last_completed_cycle_at": last_completed.get("completed_at") if last_completed else None,
        "current_cycle_id": running[0].get("cycle_id") if running else None,
        "stale_reason": (
            "scheduler disabled" if not settings.ENABLE_SCHEDULER
            else "scheduler not running" if not scheduler.running
            else None
        ),
    }
