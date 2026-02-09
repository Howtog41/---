
# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

scheduler = AsyncIOScheduler(
    timezone=timezone("Asia/Kolkata")
)
