import re
from bs4 import BeautifulSoup

# 광고/공유/푸터 등에 자주 등장하는 패턴(클래스/아이디/role/aria 등)
NOISE_PATTERNS = [
    r"\bsubscribe\b", r"advertis", r"\bad[-_]?slot\b", r"\bcookie\b",
    r"\bshare\b", r"follow\s+us", r"newsletter", r"related\s+articles",
    r"recommended", r"most\s+read", r"\bpromo\b", r"\bpaywall\b",
    r"\bfooter\b", r"\bheader\b", r"\bnav(igation)?\b", r"\bcomments?\b",
    r"\bsocial\b", r"\bsign[- ]?in\b", r"\blogin\b", r"\bsubscribe[- ]?now\b",
]
_noise_re = re.compile("|".join(NOISE_PATTERNS), re.I)

# 하드 보일러/페이월 문구(본문 텍스트에서 직접 삭제)
HARD_STRIP_PATTERNS = [
    r"\b(read more|click here|continue reading|subscribe( now| to)?)\b",
    r"\b(you’ve reached your limit|sign in to continue|access denied)\b",
    r"(자세히\s*보기|더\s*읽어보기|구독하고\s*읽기|회원\s*가입|로그인하고\s*계속)",
]
_hard_strip_re = re.compile("|".join(HARD_STRIP_PATTERNS), re.I)


def _strip_inline_boiler(text: str) -> str:
    t = _hard_strip_re.sub("", text or "")
    # 중복 구두점/여백 정리
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\.{3,}", "...", t)
    t = re.sub(r"[!?]{3,}", "!!", t)
    return t.strip()

def clean_html_to_text(html_or_summary: str | None) -> str | None:
    if not html_or_summary:
        return None
    soup = BeautifulSoup(html_or_summary, "html.parser")

    # 1) 스크립트/스타일 제거
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    # 2) role/aria/클래스/아이디 기반 노이즈 제거
    for tag in soup.find_all(True):
        # semantic role/aria-label 우선
        role = (tag.get("role") or "").lower()
        aria = (tag.get("aria-label") or "").lower()
        attrs = " ".join([tag.get("id", ""), " ".join(tag.get("class", [])), role, aria]).lower()
        if (role in {"banner", "navigation", "complementary", "contentinfo"} or
            "aria-hidden" in tag.attrs or
            (attrs and _noise_re.search(attrs))):
            tag.decompose()
            continue

        # <a>는 텍스트만 살리고 href는 버림(앵커 리스트 제거)
        if tag.name == "a" and len(tag.get_text(strip=True)) <= 2:
            tag.decompose()

        # figure/caption의 캡션류 제거(광고/출처 남발 케이스)
        if tag.name in {"figure", "figcaption"} and _noise_re.search(attrs):
            tag.decompose()

    # 3) 텍스트 추출
    text = soup.get_text(separator=" ", strip=True)
    text = _strip_inline_boiler(text)

    # 4) 공백 정리
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None
