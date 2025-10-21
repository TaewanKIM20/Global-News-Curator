import os
from transformers import pipeline

# 환경변수로 모델 교체 가능 (다국어/한국어 지원 모델을 권장)
MODEL_NAME = os.getenv("HF_SUMMARY_MODEL", "facebook/mbart-large-50-many-to-many-mmt")

_summarizer = None

def get_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = pipeline(
            "summarization",
            model=MODEL_NAME,
            tokenizer=MODEL_NAME,
            device=-1,            # CPU
        )
    return _summarizer

def summarize(text: str, max_sentences: int = 4) -> str | None:
    if not text: return None
    pipe = get_summarizer()
    # 길면 자르고, 너무 짧으면 그대로 반환
    t = text.strip()
    if len(t.split()) < 30:
        return t
    out = pipe(
        t,
        max_length=220,
        min_length=60,
        do_sample=False,
    )
    s = out[0]["summary_text"].strip()
    # 3~5문장 정도로 맞춤 (문장 split 후 상한/하한 보정)
    sents = [x.strip() for x in s.replace("\n"," ").split(". ") if x.strip()]
    if len(sents) > 5: sents = sents[:5]
    return (". ".join(sents)).strip()
