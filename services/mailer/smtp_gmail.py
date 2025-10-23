import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime, timedelta, timezone

from apps.api.models import Article
from shared.db import db
from shared.settings import settings
from services.recommend.ranker import rank_articles
from services.analyzer.sentiment import analyze_text_sentiment

GMAIL_ADDR = os.getenv("GMAIL_ADDR")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
SENDER = os.getenv("NEWSLETTER_SENDER") or GMAIL_ADDR

# 옵션 플래그(원하면 끌 수 있게)
INCLUDE_SENTIMENT = os.getenv("INCLUDE_SENTIMENT", "true").lower() in ("1","true","yes")

env = Environment(
    loader=FileSystemLoader("newsletter_templates"),
    autoescape=select_autoescape(["html"])
)

def _compute_bias_metrics(articles):
    """
    topic_id별 pos/neu/neg 집계 + 퍼센트 + 샘플수/주의 배지
    bias_index = |pos - neg| / total  (0~1)
    """
    bucket = {}
    for a in articles:
        s = getattr(a, "_sentiment", None)
        if not s:
            continue
        tid = a.topic_id if getattr(a, "topic_id", None) is not None else -1
        b = bucket.setdefault(tid, {"pos": 0, "neu": 0, "neg": 0})
        b[s["label"]] = b.get(s["label"], 0) + 1

    rows = []
    for tid, c in bucket.items():
        total = max(1, c["pos"] + c["neu"] + c["neg"])
        pos_pct = (c["pos"] / total) * 100.0
        neu_pct = (c["neu"] / total) * 100.0
        neg_pct = (c["neg"] / total) * 100.0
        bias = abs(c["pos"] - c["neg"]) / float(total)
        rows.append({
            "topic_id": tid,
            "pos": c["pos"], "neu": c["neu"], "neg": c["neg"],
            "pos_pct": pos_pct, "neu_pct": neu_pct, "neg_pct": neg_pct,
            "bias_index": bias,
            "total": total,
            "low_sample": total < 3  # 샘플 수 경고 플래그
        })

    # bias 높은 순으로 정렬 (동점 시 total 많은 순)
    rows.sort(key=lambda x: (x["bias_index"], x["total"]), reverse=True)
    return rows


def _render_daily_html(articles, prefs):
    kst = timezone(timedelta(hours=9))
    articles = _attach_per_article_sentiment(articles)

    html = env.get_template("daily.html.j2").render(
        date_str=datetime.now(kst).strftime("%Y-%m-%d %H:%M"),
        articles=articles,
        prefs=prefs,
        # 더 이상 topic_metrics는 전달하지 않음
    )
    return html


def _fetch_recent_analyzed(limit=300) -> list[Article]:
    q = (Article.query
         .filter(Article.is_duplicate.is_(False))
         .filter(Article.summary_ko.isnot(None))  # 분석 끝난 것만
         .order_by(Article.id.desc())
         .limit(limit))
    return q.all()

def build_daily_articles(limit=10, prefs_override: list[str] | None = None):
    prefs = [p.strip().lower() for p in (prefs_override or settings.USER_PREFERENCES) if p.strip()]
    candidates = _fetch_recent_analyzed(limit=300)

    if prefs:
        ranked = rank_articles(candidates, preferences=prefs, topk=limit)
        # 추천 결과가 너무 적으면 최신 fallback 혼합
        if len(ranked) < limit:
            seen = {a.id for a in ranked}
            fallback = [a for a in candidates if a.id not in seen][: (limit - len(ranked))]
            return ranked + fallback
        return ranked
    else:
        # 환경변수 취향 없으면 기존 로직대로 최신 10개
        return candidates[:limit]

def send_daily_newsletter_gmail(to_email: str, preview_count: int = 10, prefs_override: list[str] | None = None) -> dict:
    if not GMAIL_ADDR or not GMAIL_APP_PASSWORD:
        return {"sent": 0, "reason": "GMAIL_ADDR or GMAIL_APP_PASSWORD not set"}

    prefs = [p.strip().lower() for p in (prefs_override or settings.USER_PREFERENCES) if p.strip()]
    articles = build_daily_articles(preview_count, prefs_override=prefs)

    topic_metrics = []
    if INCLUDE_SENTIMENT and articles:
        for a in articles:
            base = a.content_clean or a.summary_gen or a.summary_raw or a.title
            s = analyze_text_sentiment(base or "")
            a._sentiment = s
            if s:
                a._sent_icon  = "🟢" if s["label"] == "pos" else ("🟡" if s["label"] == "neu" else "🔴")
                a._sent_label = {"pos":"긍정","neu":"중립","neg":"부정"}[s["label"]]
            else:
                a._sent_icon, a._sent_label = "⚪", "N/A"
        topic_metrics = _compute_bias_metrics(articles)

    html = _render_daily_html(articles, prefs)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Daily Global Brief (Personalized Preview)" if prefs else "Daily Global Brief (Preview)"
    msg["From"] = SENDER
    msg["To"] = to_email

    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDR, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDR, [to_email], msg.as_string())

    return {"sent": 1, "status": 200, "prefs": prefs}


def _attach_per_article_sentiment(articles: list[Article]) -> list[Article]:
    for a in articles:
        base = (a.summary_gen or a.summary_ko or a.content_clean or a.summary_raw or a.title or "") or ""
        if not base.strip():
            continue
        try:
            s = analyze_text_sentiment(base[:1200])  # 너무 길면 오래 걸리니 1200자 정도 컷
            if s:
                dist = s.get("dist", {})
                pos = float(dist.get("pos", 0.0))
                neu = float(dist.get("neu", 0.0))
                neg = float(dist.get("neg", 0.0))
                tot = max(1e-9, pos + neu + neg)
                a._sent = {
                    "label": s.get("label"),
                    "polarity": round(s.get("polarity", 0.0), 3),
                    "pos_pct": round(pos / tot * 100.0, 1),
                    "neu_pct": round(neu / tot * 100.0, 1),
                    "neg_pct": round(neg / tot * 100.0, 1),
                }
        except Exception as e:
            # 조용히 스킵 (메일 전체 실패 방지)
            print(f"[mailer] sentiment fail article_id={getattr(a,'id',None)}: {e}")
    return articles