from flask import Blueprint, jsonify
from services.collector.rss import collect_rss_batch

bp = Blueprint("health", __name__)

@bp.get("/health")
def health():
    return jsonify(ok=True)

# 수동으로 수집을 1회 실행하는 임시 엔드포인트(개발용)
@bp.post("/collect-now")
def collect_now():
    n = collect_rss_batch()
    return {"inserted": n}
