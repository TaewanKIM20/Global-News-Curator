import os, re
from typing import Optional, Dict
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TextClassificationPipeline

_MODEL_NAME = os.getenv("HF_SENTIMENT_MODEL", "cardiffnlp/twitter-xlm-roberta-base-sentiment")
_pipe: Optional[TextClassificationPipeline] = None
_RX = re.compile(r"\s+")

def _clean(s: str) -> str:
    return _RX.sub(" ", (s or "").strip())

def get_pipe() -> TextClassificationPipeline:
    global _pipe
    if _pipe is None:
        tok = AutoTokenizer.from_pretrained(_MODEL_NAME)
        mdl = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)
        _pipe = TextClassificationPipeline(
            task="sentiment-analysis",
            model=mdl,
            tokenizer=tok,
            device=-1,               # CPU
            return_all_scores=True,
            truncation=True,
        )
    return _pipe

def _norm_label(lbl: str) -> str:
    l = (lbl or "").strip().lower()
    if l in ("label_0", "neg", "negative", "negativo", "negatif", "negativ"):
        return "neg"
    if l in ("label_1", "neu", "neutral", "neutro", "neutre"):
        return "neu"
    if l in ("label_2", "pos", "positive", "positivo", "positif", "positiv"):
        return "pos"
    # 혹시 모를 기타 표기 대비
    if "neg" in l: return "neg"
    if "neu" in l: return "neu"
    if "pos" in l: return "pos"
    return "neu"  # 기본값은 중립

def analyze_text_sentiment(text: str) -> Optional[Dict]:
    t = _clean(text)
    if not t:
        return None

    out = get_pipe()(t[:4096])[0]
    scores = {"pos": 0.0, "neu": 0.0, "neg": 0.0}
    for x in out:
        k = _norm_label(x.get("label"))
        try:
            scores[k] = float(x.get("score", 0.0))
        except Exception:
            pass

    label = max(scores, key=scores.get)
    polarity = scores["pos"] - scores["neg"]
    
    return {
        "label": label,
        "score": scores[label],
        "polarity": polarity,
        "dist": scores,
    }
