import os
import re
from typing import List
from transformers import pipeline

# ---------------------------------------------------------
# 설정
# ---------------------------------------------------------
MODEL_NAME = os.getenv("HF_SUMMARY_MODEL", "facebook/mbart-large-50-many-to-many-mmt")
_summarizer = None

def get_summarizer():
    """HuggingFace summarization pipeline lazy load"""
    global _summarizer
    if _summarizer is None:
        _summarizer = pipeline(
            "summarization",
            model=MODEL_NAME,
            tokenizer=MODEL_NAME,
            device=-1,  # CPU 환경
        )
    return _summarizer


# ---------------------------------------------------------
# 문장 처리 유틸
# ---------------------------------------------------------
_SENT_SPLIT = re.compile(r"(?<=[\.!?…])\s+")

def _split_sentences(text: str) -> List[str]:
    sents = [s.strip() for s in _SENT_SPLIT.split(text.strip()) if s.strip()]
    return sents

def _merge_by_limit(sents: List[str], max_words: int) -> List[str]:
    """문장들을 max_words 단위로 합쳐 청킹"""
    chunks, cur, cnt = [], [], 0
    for s in sents:
        w = len(s.split())
        if cnt + w > max_words and cur:
            chunks.append(" ".join(cur))
            cur, cnt = [s], w
        else:
            cur.append(s)
            cnt += w
    if cur:
        chunks.append(" ".join(cur))
    return chunks


# ---------------------------------------------------------
# Summarization Core
# ---------------------------------------------------------
def _gen(pipe, text: str, max_new_tokens: int, min_length: int) -> str:
    """모델 호출 유틸 (오류 방지용 동적 길이 보정 포함)"""
    # 안전한 길이 제한 (짧은 입력 대비)
    max_new_tokens = max(80, min(max_new_tokens, 1024))
    min_length = min(min_length, int(max_new_tokens * 0.8))

    out = pipe(
        text,
        max_new_tokens=max_new_tokens,
        min_length=min_length,
        num_beams=4,
        no_repeat_ngram_size=4,
        length_penalty=0.9,  # <1.0 → 조금 더 길게 말하도록
        do_sample=False,
        truncation=True,
        clean_up_tokenization_spaces=True,
    )
    return out[0]["summary_text"].strip()


def summarize(text: str, base_min_sentences: int = 4, length_factor: float = 3.0) -> str | None:
    if not text:
        return None

    t = text.strip()
    words = t.split()
    n_words = len(words)
    if n_words < 30:
        return t  # 너무 짧은 기사면 그대로 반환

    pipe = get_summarizer()
    sents = _split_sentences(t)
    total_words = len(words)

    # ---------------------------------------------------------
    # 본 요약 수행
    # ---------------------------------------------------------
    if total_words <= 700:
        # 단일 패스 (짧은 기사)
        max_tokens = min(900, int(total_words * 0.9))
        min_len = max(80, int(total_words * 0.5))
        s = _gen(pipe, t, max_new_tokens=max_tokens, min_length=min_len)
    else:
        # 다중 청크 요약
        chunks = _merge_by_limit(sents, max_words=520)
        partials = []
        for ch in chunks:
            max_t = min(500, int(len(ch.split()) * 0.9))
            min_t = max(120, int(len(ch.split()) * 0.4))
            partials.append(_gen(pipe, ch, max_new_tokens=max_t, min_length=min_t))
        merged = " ".join(partials)

        # 최종 통합 재요약
        total_target = min(1200, int(total_words * 0.9))
        total_min = max(200, int(total_words * 0.6))
        s = _gen(pipe, merged, max_new_tokens=total_target, min_length=total_min)

    sents_out = [x.strip() for x in _SENT_SPLIT.split(s.replace("\n", " ")) if x.strip()]
    min_sents = max(3, int(base_min_sentences * length_factor))
    max_sents = 5

    if len(sents_out) > max_sents:
        sents_out = sents_out[:max_sents]

    return " ".join(sents_out).strip()
