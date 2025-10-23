import re
from typing import Tuple

_BOILERPLATE_PATTERNS = [
    r"\bhere'?s what (you|to) know\b",
    r"\bwhat (we|to) know (so far)?\b",
    r"\bread more\b",
    r"\bclick here\b",
    r"\bsubscribe (now|to)\b",
    r"\bwatch (the )?video\b",
    r"\b(opinion|editorial)\b",
    r"\bnewsletter sign[- ]?up\b",
    r"\b(as|this) (reported|reported earlier)\b",
    r"\b(continue|continued) (reading|to read)\b",
    r"여기서\s*알아야\s*할\s*것",
    r"자세히\s*보기",
    r"더\s*읽어보기",
    r"구독하고\s*읽기",
    r"회원\s*가입",
]

_MIN_CHARS = 220
_MIN_WORDS = 35

_RXES = [re.compile(pat, re.I) for pat in _BOILERPLATE_PATTERNS]
_WORD_RX = re.compile(r"\w+", re.UNICODE)

def looks_like_boilerplate(text: str) -> bool:
    if not text:
        return True
    t = text.strip()
    if len(t) < _MIN_CHARS:
        return True
    if len(_WORD_RX.findall(t)) < _MIN_WORDS:
        return True
    for rx in _RXES:
        if rx.search(t):
            return True
    return False

def strip_trailing_boiler(text: str) -> Tuple[str, bool]:
    if not text:
        return text, False
    t = re.sub(r"(?:\n|\r)\s*(read more|click here|subscribe.*)$", "", text, flags=re.I)
    t = re.sub(r"(?:\n|\r)\s*(자세히\s*보기|구독하고\s*읽기|회원\s*가입).*$", "", t)
    changed = (t != text)
    return t, changed
