from shared.db import db
from datetime import datetime
from sqlalchemy.dialects.sqlite import JSON

class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(200))
    title = db.Column(db.String(1000))
    url = db.Column(db.String(1000), unique=True, index=True)
    summary_raw = db.Column(db.Text)
    content_raw = db.Column(db.Text)      # 본문(추후 크롤러로 보강)
    published_at = db.Column(db.DateTime)
    lang = db.Column(db.String(10), default="auto")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ↓↓↓ 전처리/중복 관련 필드 추가
    content_clean = db.Column(db.Text)              # HTML/광고 제거 후 텍스트
    simhash64 = db.Column(db.String(20), index=True)  # 간단한 중복 검사용 64-bit 해시(문자열 저장)
    is_duplicate = db.Column(db.Boolean, default=False)
    duplicate_of_id = db.Column(
        db.Integer,
        db.ForeignKey('articles.id', name='fk_articles_duplicate_of_id'),
        nullable=True
    )
    
    keywords_json = db.Column(db.JSON, nullable=True)  # ["키워드1","키워드2",...]
    topic_id = db.Column(db.Integer, index=True, nullable=True)
    summary_gen = db.Column(db.Text)    # 생성 요약(원문 언어)
    summary_ko = db.Column(db.Text)
    
