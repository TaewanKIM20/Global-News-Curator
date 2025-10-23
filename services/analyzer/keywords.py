import re
import math
from collections import Counter, defaultdict
from typing import List, Tuple

# ---- 불용어 (필요 시 계속 보강) ----
STOPWORDS_EN = {
    "the","a","an","and","or","but","if","then","else","when","of","on","in","at","by",
    "to","from","for","as","is","are","was","were","be","been","being","it","this","that",
    "with","into","over","after","before","about","between","through","during","under",
    "more","most","such","no","nor","not","only","own","same","so","than","too","very",
    "can","could","should","would","may","might","will","shall","do","does","did","done",
    "s","t","re","ve","d","ll","m","don","doesn","didn","won","wouldn","shouldn","couldn",
    "today","yesterday","tomorrow","new","news","update","live","breaking"
}
STOPWORDS_KO = {
    "이","그","저","것","수","등","및","또는","그리고","그러나","때문","통해","대한","대한민국",
    "에서","으로","으로서","으로써","에게","에서의","에서의","에서","에게서","에게로","에게서도",
    "한다","했다","하며","하도록","라고","이라고","등의","중","이며","하는","한","같은","까지",
    "로서","로써","에게도","것은","것이","것을","거나","라도","라도","보다","보다도","하지만",
    "기자","사진","영상","출처","관련","기사","보도","속보","단독"
}
STOPWORDS = STOPWORDS_EN | STOPWORDS_KO

# 구/문장 구분용 구두점
SENT_DELIMS = re.compile(r"[.!?…]+\s+")
# 토큰: 영문/숫자/한글, 내부 하이픈 허용
TOKEN_RX = re.compile(r"[A-Za-z0-9가-힣]+(?:-[A-Za-z0-9가-힣]+)*")

def _normalize(txt: str) -> str:
    if not txt:
        return ""
    txt = re.sub(r"[\u200b\uFEFF]", "", txt)  # zero-width 제거
    # 따옴표/이모지/특수문자 → 공백
    txt = re.sub(r"[^\w\s\-\u3131-\u318E\uAC00-\uD7A3]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def _split_sentences(text: str) -> List[str]:
    parts = SENT_DELIMS.split(text)
    return [p.strip() for p in parts if p.strip()]

def _is_stop(token: str) -> bool:
    t = token.lower()
    if t in STOPWORDS: return True
    # 한 글자 토큰은 대부분 노이즈 (예: s, a)
    if len(t) == 1: return True
    return False

def _candidate_phrases(text: str) -> List[List[str]]:
    """
    RAKE 후보 구(phrases): 불용어를 경계로 끊고, 나머지 구간에서 토큰 시퀀스를 후보로 삼음
    """
    tokens = [t for t in TOKEN_RX.findall(text)]
    phrases, current = [], []
    for tok in tokens:
        if _is_stop(tok):
            if current:
                phrases.append(current)
                current = []
        else:
            current.append(tok)
    if current:
        phrases.append(current)
    # 길이가 너무 긴 후보는 잘라냄(최대 4단어)
    trimmed = []
    for p in phrases:
        if len(p) > 4:
            # 윈도우로 잘라 후보 여러 개로 생성
            for i in range(len(p)-3):
                trimmed.append(p[i:i+4])
        else:
            trimmed.append(p)
    # 길이 1 이상만
    return [p for p in trimmed if len(p) >= 1]

def _rake_score(phrases: List[List[str]]) -> Tuple[dict, Counter]:
    """
    기본 RAKE: 각 토큰의 degree(이웃 수)와 freq로 토큰 스코어 계산 후 구 스코어 합산
    """
    freq = Counter()
    degree = Counter()
    for p in phrases:
        unique = [w.lower() for w in p]
        l = len(unique)
        for w in unique:
            freq[w] += 1
            degree[w] += (l - 1)  # 자기 제외 동반자 수
    token_score = {}
    for w in freq:
        token_score[w] = degree[w] + freq[w]
    # 구 스코어
    phrase_score = {}
    for p in phrases:
        sc = sum(token_score[w.lower()] for w in p)
        phrase_score[" ".join(p)] = sc
    return phrase_score, freq

def _boost_title(phrase_score: dict, title: str, boost: float = 1.25):
    title_norm = _normalize(title).lower()
    if not title_norm: return
    for ph in list(phrase_score.keys()):
        low = ph.lower()
        if low in title_norm:
            phrase_score[ph] *= boost
        else:
            # 단어 단위 포함도 체크
            words = set(low.split())
            if all(w in title_norm for w in words):
                phrase_score[ph] *= (boost - 0.1)

def _boost_capitalized(phrase_score: dict, text: str, boost: float = 1.1):
    # 대문자 시작/고유명사처럼 보이는 토큰이 있는 구에 소폭 가중
    caps = set(w for w in TOKEN_RX.findall(text) if w[:1].isupper() and w[1:].islower())
    if not caps: return
    for ph in list(phrase_score.keys()):
        if any(tok in caps for tok in ph.split()):
            phrase_score[ph] *= boost

def _dedup_phrases(cands: List[Tuple[str, float]], topk: int) -> List[str]:
    def jaccard(a: str, b: str) -> float:
        sa, sb = set(a.split()), set(b.split())
        if not sa or not sb: return 0.0
        return len(sa & sb) / len(sa | sb)

    selected: List[str] = []
    for ph, _ in cands:
        keep = True
        for s in selected:
            if ph == s: 
                keep = False
                break
            if ph in s or s in ph:
                keep = False
                break
            if jaccard(ph, s) >= 0.6:
                keep = False
                break
        if keep:
            selected.append(ph)
        if len(selected) >= topk:
            break
    return selected

def extract_keywords(text: str, topk: int = 8, title: str = "") -> List[str]:
    t = _normalize(text)
    ti = _normalize(title)
    corpus = f"{ti}. {t}".strip()

    if not corpus:
        return []

    # --- KeyBERT가 있으면 먼저 시도 ---
    try:
        from keybert import KeyBERT  # noqa
        import spacy  # noqa
        # 가벼운 en_core_web_sm가 없으면 자동 실패 -> except에서 RAKE로
        nlp = spacy.load("en_core_web_sm")
        kw_model = KeyBERT()
        doc = nlp(corpus)
        # 명사/고유명사만
        tokens = [tok.text for tok in doc if tok.pos_ in ["NOUN","PROPN"] and not tok.is_stop]
        if tokens:
            joined = " ".join(tokens)
        else:
            joined = corpus
        kws = kw_model.extract_keywords(
            joined,
            keyphrase_ngram_range=(1,2),
            stop_words="english",
            top_n=topk*2,  # 넉넉히 뽑아서 이후 정제
        )
        # 스코어로 정렬 → 중복 제거
        cand = [(k.strip(), float(s)) for k, s in kws if k.strip()]
        cand.sort(key=lambda x: x[1], reverse=True)
        out = _dedup_phrases(cand, topk)
        if out:
            return out
    except Exception:
        pass  # KeyBERT 미설치/로딩 실패 → RAKE fallback

    # --- RAKE Fallback ---
    phrases = _candidate_phrases(corpus)
    if not phrases:
        return []
    ps, freq = _rake_score(phrases)
    _boost_title(ps, ti)
    _boost_capitalized(ps, corpus)

    # 길이/빈도 기반 약한 정규화 (긴 구에 약간 가산점)
    scored = []
    for ph, sc in ps.items():
        length_bonus = 1.0 + 0.05 * (len(ph.split()) - 1)
        scored.append((ph, sc * length_bonus))
    scored.sort(key=lambda x: x[1], reverse=True)

    # 너무 일반적인 단어만으로 구성된 후보 제거 (예: government, people)
    def is_generic(p: str) -> bool:
        toks = [w.lower() for w in p.split()]
        # 고유명사/지명/인명일 가능성(대문자 시작 등)은 살려둠
        if any(w[:1].isupper() for w in p.split()): 
            return False
        generic_pool = {"government","president","minister","people","country","policy","issue","news","update"}
        return all(w in generic_pool or w in STOPWORDS for w in toks)

    cleaned = [(ph, sc) for ph, sc in scored if not is_generic(ph)]
    return _dedup_phrases(cleaned, topk)
