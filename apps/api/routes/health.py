from flask import Blueprint, jsonify
from services.collector.rss import collect_rss_batch
from services.preprocess.pipeline import preprocess_new_articles
from services.mailer.smtp_gmail import send_daily_newsletter_gmail
from services.analyzer.pipeline import analyze_articles

bp = Blueprint("health", __name__)

@bp.get("/health")
def health():
    return jsonify(ok=True)

# 수동으로 수집을 1회 실행하는 임시 엔드포인트(개발용)
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
    from services.analyzer.pipeline import analyze_articles
    r = analyze_articles(batch_size=3)   # ← 3~5로 줄여서 속도 확인
    return r


@bp.post("/send-preview-gmail")
def send_preview_gmail():
    to = "NewscuratorNoreply@gmail.com"
    r = send_daily_newsletter_gmail(to)
    return r