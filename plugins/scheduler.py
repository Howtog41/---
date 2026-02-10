from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone
from plugins.mcqsend import send_mcqs

TZ = timezone("Asia/Kolkata")
scheduler = AsyncIOScheduler(timezone=TZ)


def start_scheduler():
    if not scheduler.running:
        scheduler.start()


def restore_jobs(app, schedules):
    for s in schedules.find({"status": "active"}):
        h, m = map(int, s["time"].split(":"))
        scheduler.add_job(
            send_mcqs,
            "cron",
            hour=h,
            minute=m,
            args=[str(s["_id"]), app.bot, schedules, app.bot_data["users"]],
            id=str(s["_id"]),
            replace_existing=True
        )


def schedule_job(schedule, bot, schedules):
    h, m = map(int, schedule["time"].split(":"))
    scheduler.add_job(
        send_mcqs,
        "cron",
        hour=h,
        minute=m,
        args=[str(schedule["_id"]), bot, schedules, users],
        id=str(schedule["_id"]),
        replace_existing=True
    )


def remove_job(sid):
    try:
        scheduler.remove_job(str(sid))
    except:
        pass
