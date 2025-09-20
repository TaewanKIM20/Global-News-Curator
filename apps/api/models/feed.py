from shared.db import db
from datetime import datetime

class Feed(db.Model):
    __tablename__ = "feeds"
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), unique=True, nullable=False)
    title = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
