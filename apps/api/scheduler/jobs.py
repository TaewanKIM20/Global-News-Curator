from apscheduler.triggers.cron import CronTrigger
from flask import current_app
from services.collector.rss import collect_rss_batch

def _run_daily_pipeline(app):
    with app.app_context():
        current_app.logger.info("[pipeline] start daily collect")
        n = collect_rss_batch()
        current_app.logger.info(f"[pipeline] collected {n} items")

def register_jobs(scheduler, app):
    # 매일 07:30 KST에 실행
    scheduler.add_job(
        _run_daily_pipeline,
        #trigger=CronTrigger(hour=7, minute=30),
        trigger=CronTrigger(minute="*/2"),
        args=[app],
        id="daily_pipeline",
        replace_existing=True,
    )
