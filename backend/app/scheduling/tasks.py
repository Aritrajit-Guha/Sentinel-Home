"""Scheduled backend monitoring entry point."""

from app.services.monitoring_service import run_monitoring_cycle


def check_all_households():
    return run_monitoring_cycle()
