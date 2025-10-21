from sklearn.feature_extraction.text import TfidfVectorizer
import re

def _normalize(txt: str) -> str:
    if not txt: return ""
    # 한/영/숫자 위주로 간단 정규화
    txt = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt

def extract_keywords(text: str, topk: int = 8) -> list[str]:
    text = _normalize(text)
    if not text: return []
    # 단일 문서 TF-IDF → 토큰 중요도 상위
    vec = TfidfVectorizer(
        ngram_range=(1,2),
        max_features=5000,
        min_df=1,
        token_pattern=r"(?u)\b\w+\b"
    )
    X = vec.fit_transform([text])
    vocab = vec.get_feature_names_out()
    scores = X.toarray()[0]
    idx = scores.argsort()[::-1][:topk]
    return [vocab[i] for i in idx]
