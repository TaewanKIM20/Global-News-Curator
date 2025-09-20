import feedparser
from datetime import datetime, timezone
from shared.settings import settings
from shared.db import db
from apps.api.models import Article, Feed
from urllib.parse import urlparse

def _ensure_feed(url, title=None):
    feed = Feed.query.filter_by(url=url).first()
    if not feed:
        feed = Feed(url=url, title=title)
        db.session.add(feed)
        db.session.commit()
    return feed

def _to_datetime(entry):
    if getattr(entry, "published_parsed", None):
        # UTC 기준으로 저장 후 나중에 표시시 KST 변환
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return None

def collect_rss_once(feed_url: str) -> int:
    parsed = feedparser.parse(feed_url)
    title = parsed.feed.get("title", urlparse(feed_url).netloc)
    _ensure_feed(feed_url, title)

    inserted = 0
    for e in parsed.entries:
        url = e.get("link")
        if not url:
            continue
        if Article.query.filter_by(url=url).first():
            continue
        art = Article(
            source=title,
            title=e.get("title"),
            url=url,
            summary_raw=e.get("summary"),
            published_at=_to_datetime(e),
            lang="auto",
        )
        db.session.add(art)
        inserted += 1

    if inserted:
        db.session.commit()
    return inserted

def collect_rss_batch() -> int:
    total = 0
    for u in settings.FEEDS:
        try:
            total += collect_rss_once(u)
        except Exception as ex:
            print(f"[collector] error {u}: {ex}")
    return total
