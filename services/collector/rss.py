import feedparser
from datetime import datetime, timezone
from shared.settings import settings
from shared.db import db
from apps.api.models import Article, Feed
from urllib.parse import urlparse

def _ensure_feed(url, title=None):
    """중복 Feed 삽입 방지 + 세션 rollback 안전 처리"""
    feed = Feed.query.filter_by(url=url).first()
    if feed:
        # 이미 존재 → 제목 업데이트만 필요할 경우 업데이트
        if title and feed.title != title:
            feed.title = title
            db.session.commit()
        return feed

    try:
        feed = Feed(url=url, title=title)
        db.session.add(feed)
        db.session.commit()
        return feed
    except Exception as e:
        db.session.rollback() 
        print(f"[collector] ⚠️ feed insert error: {e}")
        return Feed.query.filter_by(url=url).first()


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
            added = collect_rss_once(u)
            total += added
            print(f"[collector] {u} → {added} new articles")
        except Exception as ex:
            db.session.rollback()
            print(f"[collector] ⚠️ error {u}: {ex}")
            continue
    print(f"[collector] ✅ total collected: {total}")
    return total


def save_item(item):
    # item.url 은 필수
    if Article.query.filter_by(url=item.url).first():
        return False  # 이미 존재

    a = Article(
        source=item.source,
        title=item.title,
        url=item.url,
        summary_raw=item.summary,   # RSS 요약
        content_raw=None,
        published_at=item.published_at,
        lang="auto"
    )
    db.session.add(a)
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        return False