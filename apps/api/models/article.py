from shared.db import db
from datetime import datetime

class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(200))
    title = db.Column(db.String(1000))
    url = db.Column(db.String(1000), unique=True, index=True)
    summary_raw = db.Column(db.Text)     # RSS 요약(있으면)
    content_raw = db.Column(db.Text)     # 본문(추후 크롤러로 채움)
    published_at = db.Column(db.DateTime)
    lang = db.Column(db.String(10), default="auto")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
