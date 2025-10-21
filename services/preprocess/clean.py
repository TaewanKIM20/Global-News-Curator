import re
from bs4 import BeautifulSoup

# 불필요 블록 후보(광고/공유/푸터 등에 자주 등장)
NOISE_PATTERNS = [
    r"subscribe", r"advertis", r"ad-", r"cookie", r"share", r"follow us",
    r"newsletter", r"related articles", r"recommended", r"most read",
]
_noise_re = re.compile("|".join(NOISE_PATTERNS), re.I)

def clean_html_to_text(html_or_summary: str | None) -> str | None:
    if not html_or_summary:
        return None
    soup = BeautifulSoup(html_or_summary, "html.parser")

    # 스크립트/스타일 제거
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # 광고/잡다 블록 간단 필터링(클래스/아이디 힌트)
    for tag in soup.find_all(True):
        attrs = " ".join([tag.get("id",""), " ".join(tag.get("class", []))]).lower()
        if attrs and _noise_re.search(attrs):
            tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    # 공백 정리
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None
