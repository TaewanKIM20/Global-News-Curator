from shared.db import db
from apps.api.models import Article
from services.preprocess.clean import clean_html_to_text
from services.preprocess.boilerplate import looks_like_boilerplate, strip_boiler_leading_trailing
from services.preprocess.dedup import simhash64, is_near_duplicate

def preprocess_new_articles(batch_size: int = 100) -> dict:
    q = (Article.query
         .filter(Article.content_clean.is_(None))
         .order_by(Article.id.desc())
         .limit(batch_size))
    items = q.all()
    if not items:
        return {"processed": 0, "duplicates": 0, "dropped_low_quality": 0}

    # 최근 캐시(소스별 + 글로벌)
    recent = (Article.query
              .filter(Article.simhash64.isnot(None))
              .order_by(Article.id.desc())
              .limit(1500)
              .all())

    recent_by_source: dict[str, list[Article]] = {}
    for r in recent:
        recent_by_source.setdefault(r.source or "", []).append(r)

    processed = 0
    duplicates = 0
    dropped_low_quality = 0

    for a in items:
        # 1) Raw 선택
        raw = a.content_raw or a.summary_raw or a.title

        # 2) HTML -> 텍스트
        cleaned = clean_html_to_text(raw) or ""

        # 3) 보일러 앞/뒤 제거
        cleaned, _ = strip_boiler_leading_trailing(cleaned)

        # 4) 품질 가드레일(너무 짧거나 티저/페이월 등)
        if looks_like_boilerplate(cleaned):
            # 품질이 낮으면 요약/발송 파이프라인에서 제외(필요 시 상태 필드 사용)
            a.content_clean = cleaned
            a.is_duplicate = False
            a.duplicate_of_id = None
            if hasattr(a, "quality_flags"):
                a.quality_flags = "low_quality/boilerplate"
            dropped_low_quality += 1
            processed += 1
            continue

        a.content_clean = cleaned
        if hasattr(a, "content_clean_len"):
            a.content_clean_len = len(cleaned)

        # 5) simhash(제목 가중)
        sh = simhash64(cleaned, title=(a.title or ""))
        a.simhash64 = str(sh) if sh else None

        # 6) 근접 중복 판정(동일 소스 우선, 없으면 글로벌)
        dup_target = None
        pools = []
        if (a.source or "") in recent_by_source:
            pools.append(recent_by_source[a.source or ""])
        pools.append(recent)  # 글로벌 백업

        for pool in pools:
            for r in pool:
                if not r.simhash64:
                    continue
                try:
                    rh = int(r.simhash64)
                except Exception:
                    continue
                if is_near_duplicate(sh, rh, char_len=len(cleaned), base_threshold=None):
                    dup_target = r
                    break
            if dup_target:
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
    return {
        "processed": processed,
        "duplicates": duplicates,
        "dropped_low_quality": dropped_low_quality
    }
