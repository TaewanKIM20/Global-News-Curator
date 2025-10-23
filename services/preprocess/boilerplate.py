import re
from typing import Tuple

# 기존 패턴 보강(영/한 혼합 + 뉴스레터/티저/요지형)
_BOILERPLATE_PATTERNS = [
    r"\bhere'?s what (you|to) know\b",
    r"\bwhat (we|to) know( so far)?\b",
    r"\bread more\b",
    r"\bclick here\b",
    r"\bsubscribe( now| to)?\b",
    r"\bwatch( the)? video\b",
    r"\b(opinion|editorial)\b",
    r"\bnewsletter sign[- ]?up\b",
    r"\b(as|this) (reported|reported earlier)\b",
    r"\b(continue|continued) (reading|to read)\b",
    r"\btop stories\b", r"\bmost read\b", r"\brecommended\b", r"\btrending\b",
    r"여기서\s*알아야\s*할\s*것", r"자세히\s*보기", r"더\s*읽어보기",
    r"구독하고\s*읽기", r"회원\s*가입", r"로그인하고\s*계속",
]

# 최소 요건 + 문장/고유어 비율 가드레일
_MIN_CHARS = 280
_MIN_WORDS = 45
_MIN_SENTENCES = 3
_MIN_UNIQUE_RATIO = 0.35  # 고유 단어 비율

_RXES = [re.compile(pat, re.I) for pat in _BOILERPLATE_PATTERNS]
_WORD_RX = re.compile(r"[A-Za-z0-9가-힣']+", re.UNICODE)
_SENT_RX = re.compile(r"[.!?…]+[\s\"]+")

def _unique_ratio(words: list[str]) -> float:
    if not words:
        return 0.0
    return len(set(words)) / max(1, len(words))

def looks_like_boilerplate(text: str) -> bool:
    if not text:
        return True
    t = text.strip()

    # 길이/단어/문장 수
    if len(t) < _MIN_CHARS:
        return True
    words = _WORD_RX.findall(t)
    if len(words) < _MIN_WORDS:
        return True
    if len(_SENT_RX.split(t)) < _MIN_SENTENCES:
        return True
    if _unique_ratio([w.lower() for w in words]) < _MIN_UNIQUE_RATIO:
        return True

    # 패턴 매칭
    for rx in _RXES:
        if rx.search(t):
            return True
    return False

def strip_boiler_leading_trailing(text: str) -> Tuple[str, bool]:
    if not text:
        return text, False
    orig = text

    # 꼬리(CTA/구독/더보기) 제거
    t = re.sub(r"(?:\n|\r|\s)+(read more|click here|subscribe.*|자세히\s*보기|구독하고\s*읽기|회원\s*가입|로그인하고\s*계속).*$",
               "", text, flags=re.I)

    # 머리(“Here’s what to know” 등) 제거
    t = re.sub(r"^(here'?s what (you|to) know|what (we|to) know( so far)?|top stories|most read|recommended)\W+",
               "", t, flags=re.I)

    t = t.strip()
    return (t, t != orig)
