# services/recommend/ranker.py
import re
from typing import Iterable, Tuple
from services.recommend.taxonomy import CATEGORY_LEXICON

_WORD = re.compile(r"[0-9A-Za-z가-힣]+")

def _normalize(s: str) -> list[str]:
    if not s: return []
    return [w.lower() for w in _WORD.findall(s)]

def _pref_terms(preferences: Iterable[str]) -> set[str]:
    terms = set()
    for p in preferences:
        lex = CATEGORY_LEXICON.get(p.lower(), [])
        for t in lex:
            terms.add(t.lower())
    return terms

def score_article(article, preferences: list[str]) -> Tuple[float, list[str]]:
    if not preferences:
        return 0.0, []

    prefs = [p.strip().lower() for p in preferences if p.strip()]
    term_set = _pref_terms(prefs)
    if not term_set:
        return 0.0, []

    # 후보 텍스트 구성
    title = article.title or ""
    kw = " ".join(article.keywords_json or [])
    body = (article.summary_gen or article.content_clean or article.summary_raw or "")

    tokens_title = _normalize(title)
    tokens_kw    = _normalize(kw)
    tokens_body  = _normalize(body)

    matched = set()
    # 토큰 기반 매칭
    for tk in tokens_title + tokens_kw + tokens_body:
        if tk in term_set:
            matched.add(tk)

    w_kw, w_title, w_body = 3.0, 2.0, 1.0

    s_kw    = sum(1 for tk in tokens_kw if tk in term_set) * w_kw
    s_title = sum(1 for tk in tokens_title if tk in term_set) * w_title
    s_body  = sum(1 for tk in tokens_body if tk in term_set) * w_body

    score = s_kw + s_title + s_body

    return float(score), sorted(matched)

def rank_articles(articles: list, preferences: list[str], topk: int = 10) -> list:
    scored = []
    for a in articles:
        s, matched = score_article(a, preferences)
        if s <= 0:
            continue
        setattr(a, "_rec_score", s)
        setattr(a, "_rec_matched", matched)
        scored.append(a)

    scored.sort(key=lambda x: (getattr(x, "_rec_score", 0.0), x.id), reverse=True)
    return scored[:topk]
