from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.scheduling.tasks import check_all_households

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(check_all_households, "interval", minutes=5)
    scheduler.start()
