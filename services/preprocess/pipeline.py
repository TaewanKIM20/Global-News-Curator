from shared.db import db
from apps.api.models import Article
from services.preprocess.clean import clean_html_to_text
from services.preprocess.dedup import simhash64, is_near_duplicate

def preprocess_new_articles(batch_size: int = 100) -> dict:
    """
    content_clean/simhash가 아직 없는 기사 위주로 전처리.
    간단한 중복 판정: 같은 source 내 최근 기사들과 비교.
    """
    q = (Article.query
         .filter(Article.content_clean.is_(None))
         .order_by(Article.id.desc())
         .limit(batch_size))
    items = q.all()
    if not items:
        return {"processed": 0, "duplicates": 0}

    # 최근 1000건 정도의 해시 캐시(소스별)
    recent = (Article.query
              .filter(Article.simhash64.isnot(None))
              .order_by(Article.id.desc())
              .limit(1000)
              .all())

    # 소스별 목록으로 캐시 구성
    recent_by_source: dict[str, list[Article]] = {}
    for r in recent:
        recent_by_source.setdefault(r.source or "", []).append(r)

    processed = 0
    duplicates = 0

    for a in items:
        # 클린 텍스트 우선: content_raw 있으면 그걸, 없으면 summary_raw
        raw = a.content_raw or a.summary_raw or a.title
        cleaned = clean_html_to_text(raw)
        a.content_clean = cleaned

        # simhash 계산
        sh = simhash64((a.title or "") + " " + (cleaned or ""))
        a.simhash64 = str(sh) if sh else None

        # 근접 중복 판정(같은 source 내에서 우선 확인)
        dup_target = None
        if sh and (a.source or "") in recent_by_source:
            for r in recent_by_source[a.source or ""]:
                try:
                    rh = int(r.simhash64)
                except Exception:
                    continue
                if is_near_duplicate(sh, rh, threshold=8):
                    dup_target = r
                    break

        if dup_target:
            a.is_duplicate = True
            a.duplicate_of_id = dup_target.id
            duplicates += 1
        else:
            a.is_duplicate = False
            a.duplicate_of_id = None

        processed += 1

    db.session.commit()
    return {"processed": processed, "duplicates": duplicates}
