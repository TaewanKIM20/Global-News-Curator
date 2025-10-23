import concurrent.futures
from shared.db import db
from apps.api.models import Article
from services.analyzer.keywords import extract_keywords
from services.translate.translate import translate_to_ko
from services.analyzer.byline import pick_author


def _analyze_single_article(a, lda):
    from services.analyzer.summarize import summarize

    base_text = (a.content_clean or a.summary_raw or a.title or "")
    if not base_text.strip():
        return None

    try:
        # 1) 키워드
        a.keywords_json = extract_keywords(base_text, topk=8, title=(a.title or ""))

        # 2) 토픽
        a.topic_id = lda.infer_topic(base_text)

        # 3) 요약 (길게)
        long_sum = summarize(base_text, base_min_sentences=4, length_factor=3.0)
        a.summary_gen = long_sum
        a.summary_ko = translate_to_ko(long_sum or base_text, source_lang=None)

        # 4) 기자 이름 추출
        author = pick_author(a)
        if hasattr(a, "author") and (author and not a.author):
            a.author = author
        elif hasattr(a, "meta_json"):
            try:
                meta = a.meta_json or {}
                if author:
                    meta["author_extracted"] = author
                a.meta_json = meta
            except Exception:
                pass

        return a
    except Exception as e:
        print(f"[analyzer] ⚠️ article {a.id} failed: {e}")
        return None


def analyze_articles(batch_size: int = 50) -> dict:
    from services.analyzer.topics import TinyLDAModel

    q = (Article.query
         .filter(Article.is_duplicate.is_(False))
         .filter(Article.summary_gen.is_(None))
         .order_by(Article.id.desc())
         .limit(batch_size))
    items = q.all()
    if not items:
        return {"analyzed": 0}

    # LDA 학습
    recent = (Article.query
              .filter(Article.content_clean.isnot(None))
              .order_by(Article.id.desc())
              .limit(300)
              .all())
    lda = TinyLDAModel(num_topics=5)
    lda.fit([a.content_clean or "" for a in recent])

    analyzed = []
    # CPU 4코어 기준: 4개 병렬 워커
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(_analyze_single_article, a, lda) for a in items]
        for f in concurrent.futures.as_completed(futures):
            result = f.result()
            if result:
                analyzed.append(result)

    # DB에 저장
    try:
        db.session.bulk_save_objects(analyzed)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[analyzer] ⚠️ commit failed: {e}")

    return {"analyzed": len(analyzed)}
