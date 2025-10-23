from apscheduler.triggers.cron import CronTrigger
from flask import current_app
from services.collector.rss import collect_rss_batch
from services.preprocess.pipeline import preprocess_new_articles
from services.analyzer.pipeline import analyze_articles
from services.mailer.smtp_gmail import send_daily_newsletter_gmail

def _run_daily_pipeline(app):
    with app.app_context():
        current_app.logger.info("[pipeline] start daily collect")
        n = collect_rss_batch()
        current_app.logger.info(f"[pipeline] collected {n} items")

        current_app.logger.info("[pipeline] preprocess")
        r1 = preprocess_new_articles()
        current_app.logger.info(f"[pipeline] preprocessed: {r1}")

        current_app.logger.info("[pipeline] analyze")
        r2 = analyze_articles()
        current_app.logger.info(f"[pipeline] analyzed: {r2}")
        
def register_jobs(scheduler, app):
    # 매일 07:30 KST에 실행
    scheduler.add_job(
        _run_daily_pipeline,
        trigger=CronTrigger(hour=7, minute=30),
        #trigger=CronTrigger(minute="*/2"),
        args=[app],
        id="daily_pipeline",
        replace_existing=True,
    )
