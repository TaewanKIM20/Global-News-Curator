import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime, timedelta, timezone

from apps.api.models import Article
from shared.db import db

GMAIL_ADDR = os.getenv("GMAIL_ADDR")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
SENDER = os.getenv("NEWSLETTER_SENDER") or GMAIL_ADDR

# Jinja2 템플릿 환경 (기존 daily.html.j2 재사용)
env = Environment(
    loader=FileSystemLoader("newsletter_templates"),
    autoescape=select_autoescape(["html"])
)

def _render_daily_html(articles):
    kst = timezone(timedelta(hours=9))
    html = env.get_template("daily.html.j2").render(
        date_str=datetime.now(kst).strftime("%Y-%m-%d %H:%M"),
        articles=articles
    )
    return html

def build_daily_articles(limit=10):
    q = (Article.query
         .filter(Article.is_duplicate.is_(False))
         .filter(Article.summary_ko.isnot(None))
         .order_by(Article.id.desc())
         .limit(limit))
    return q.all()

def send_daily_newsletter_gmail(to_email: str, preview_count: int = 10) -> dict:
    if not GMAIL_ADDR or not GMAIL_APP_PASSWORD:
        return {"sent": 0, "reason": "GMAIL_ADDR or GMAIL_APP_PASSWORD not set"}

    articles = build_daily_articles(preview_count)
    html = _render_daily_html(articles)

    # MIME 메일 생성
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Daily Global Brief (Preview)"
    msg["From"] = SENDER
    msg["To"] = to_email

    part_html = MIMEText(html, "html", "utf-8")
    msg.attach(part_html)

    # Gmail SMTP over SSL
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDR, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDR, [to_email], msg.as_string())

    return {"sent": 1, "status": 200}
