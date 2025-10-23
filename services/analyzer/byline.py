import re
from typing import Optional

# 흔한 패턴들 (영문/국문)
_BYLINE_RXES = [
    re.compile(r"^\s*(?:By|BY)\s+([A-Z][A-Za-z\.\-'\s]+)\s*(?:,.*)?$", re.M),
    re.compile(r"\bBy\s+([A-Z][A-Za-z\.\-'\s]+)\b"),
    re.compile(r"\b([A-Z][A-Za-z\.\-'\s]+)\s+for\s+[A-Z][A-Za-z\s]+"),
    re.compile(r"\b기자[:\s]+\s*([가-힣]{2,4})\b"),
    re.compile(r"\b([가-힣]{2,4})\s*기자\b"),
    re.compile(r"\b작성자[:\s]+\s*([가-힣A-Za-z\.\-'\s]+)\b"),
]

def extract_author_from_text(text: str | None) -> Optional[str]:
    if not text:
        return None
    t = text.strip()
    for rx in _BYLINE_RXES:
        m = rx.search(t)
        if m:
            name = m.group(1).strip()
            # 이름이 너무 길거나 이상하면 버림
            if 2 <= len(name) <= 60:
                return name
    return None

def pick_author(a) -> Optional[str]:
    # 1) 명시 필드
    for attr in ("author", "byline", "authors"):
        if hasattr(a, attr):
            v = getattr(a, attr)
            if v:
                return str(v).strip()

    # 2) meta_json 같은 필드에 들어있을 수 있음
    for attr in ("meta_json", "metadata", "extra"):
        if hasattr(a, attr):
            v = getattr(a, attr)
            if isinstance(v, dict):
                for k in ("author", "byline"):
                    if v.get(k):
                        return str(v[k]).strip()

    # 3) 원문 텍스트에서 추출
    for field in ("content_raw", "summary_raw", "content_clean"):
        if hasattr(a, field) and getattr(a, field):
            name = extract_author_from_text(getattr(a, field))
            if name:
                return name

    return None
