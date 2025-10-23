# apps/api/routes/health.py
from flask import Blueprint, jsonify, current_app
from services.collector.rss import collect_rss_batch
from services.preprocess.pipeline import preprocess_new_articles
from services.mailer.smtp_gmail import send_daily_newsletter_gmail
import os, threading
from shared.db import db

bp = Blueprint("health", __name__)

@bp.get("/health")
def health():
    return jsonify(ok=True)

@bp.post("/collect-now")
def collect_now():
    n = collect_rss_batch()
    return {"inserted": n}

@bp.post("/preprocess-now")
def preprocess_now():
    result = preprocess_new_articles()
    return result

@bp.post("/analyze-now")
def analyze_now():
    """
    최근 '요약 미완료' 기사 5개만 수동 분석.
    - dev reloader의 중복 실행 방지
    - 백그라운드 스레드에서 app_context 활성화
    """
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return {"skipped": "reloader process"}

    app = current_app._get_current_object()

    def _run():
        from services.analyzer.pipeline import analyze_articles
        # 컨텍스트를 열고, 그 안에서 remove()까지 처리
        with app.app_context():
            try:
                r = analyze_articles(batch_size=5)   # 딱 5개만
                current_app.logger.info(f"[manual analyze] analyzed: {r}")
            finally:
                db.session.remove()

    t = threading.Thread(target=_run, name="manual-analyze", daemon=True)
    t.start()
    return {"status": "started", "batch_size": 5}

@bp.post("/send-preview-gmail")
def send_preview_gmail():
    to = os.getenv("NEWSLETTER_RECEIVER")
    r = send_daily_newsletter_gmail(to)
    return r