from shared.db import db
from apps.api.models import Article
from services.analyzer.keywords import extract_keywords
from services.analyzer.topics import TinyLDAModel
from services.analyzer.summarize import summarize
from services.translate.translate import translate_to_ko

def analyze_articles(batch_size: int = 50) -> dict:
    # 요약/키워드 없는 최신 기사 배치
    q = (Article.query
         .filter(Article.is_duplicate.is_(False))
         .filter(Article.summary_gen.is_(None))
         .order_by(Article.id.desc())
         .limit(batch_size))
    items = q.all()
    if not items:
        return {"analyzed": 0}

    # 토픽 모델은 최근 컨텐츠로 가볍게 적합
    recent = (Article.query
              .filter(Article.content_clean.isnot(None))
              .order_by(Article.id.desc())
              .limit(300)
              .all())
    lda = TinyLDAModel(num_topics=5)
    lda.fit([a.content_clean or "" for a in recent])

    cnt = 0
    for a in items:
        base_text = (a.content_clean or a.summary_raw or a.title or "")
        # 키워드(제목+본문 조합)
        a.keywords_json = extract_keywords((a.title or "") + " " + base_text, topk=8)

        # 토픽 id
        a.topic_id = lda.infer_topic(base_text)

        # 요약(생성형)
        a.summary_gen = summarize(base_text)
        a.summary_ko = translate_to_ko(a.summary_gen or base_text, source_lang=None)

        cnt += 1

    db.session.commit()
    return {"analyzed": cnt}
