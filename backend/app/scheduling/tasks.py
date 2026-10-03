"""Scheduled backend monitoring entry point."""

from app.services.monitoring_service import run_monitoring_cycle
from app.services.delivery_service import process_pending_alerts


def check_all_households():
    return run_monitoring_cycle()


def check_pending_alerts():
    return process_pending_alerts()
