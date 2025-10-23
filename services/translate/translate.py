import os, time, json, html, requests, logging
from typing import Optional
from langdetect import detect, DetectorFactory

logger = logging.getLogger(__name__)
DetectorFactory.seed = 0

PAPAGO_ID = os.getenv("PAPAGO_CLIENT_ID")
PAPAGO_SECRET = os.getenv("PAPAGO_CLIENT_SECRET")
GOOGLE_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")
TRANSLATE_PROVIDER = os.getenv("TRANSLATE_PROVIDER", "auto")  # auto|papago|google|none

_cache: dict[tuple[str, str], str] = {}

# -------------------------
# 유틸 함수
# -------------------------

def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        mapping = {
            "zh-cn": "zh-CN",
            "zh-tw": "zh-TW",
            "en": "en",
            "ja": "ja",
            "fr": "fr",
            "de": "de",
            "ru": "ru",
            "ko": "ko",
        }
        return mapping.get(lang, lang)
    except Exception:
        return "auto"

def _retry(func, tries=3, backoff=1.5):
    for i in range(tries):
        try:
            return func()
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(backoff ** i)

def _split_text(text: str, max_len: int = 4800) -> list[str]:
    parts = []
    while len(text) > max_len:
        cut = text[:max_len].rsplit('.', 1)[0]
        parts.append(cut)
        text = text[len(cut):]
    if text.strip():
        parts.append(text)
    return parts

def _postprocess_korean(text: str) -> str:
    text = text.replace(" - ", " — ")
    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")
    text = text.replace("“ ", "“").replace(" ”", "”")
    return text.strip()

# -------------------------
# 번역 본체
# -------------------------

def translate_to_ko(text: str, source_lang: Optional[str] = None) -> str:
    if not text:
        return text

    # HTML 엔티티 제거
    text = html.unescape(text.strip())

    # 언어 감지
    if not source_lang or source_lang == "auto":
        source_lang = detect_language(text)

    key = (text[:4000], source_lang)
    if key in _cache:
        return _cache[key]

    def try_papago():
        url = "https://openapi.naver.com/v1/papago/n2mt"
        headers = {
            "X-Naver-Client-Id": PAPAGO_ID,
            "X-Naver-Client-Secret": PAPAGO_SECRET,
        }
        data = {"source": source_lang, "target": "ko", "text": text[:4900]}
        r = requests.post(url, headers=headers, data=data, timeout=15)
        r.raise_for_status()
        return r.json()["message"]["result"]["translatedText"]

    def try_google():
        url = f"https://translation.googleapis.com/language/translate/v2?key={GOOGLE_KEY}"
        parts = _split_text(text)
        results = []
        for p in parts:
            payload = {"q": p, "target": "ko"}
            if source_lang and source_lang != "auto":
                payload["source"] = source_lang
            r = requests.post(url, json=payload, timeout=15)
            r.raise_for_status()
            results.append(r.json()["data"]["translations"][0]["translatedText"])
        return " ".join(results)

    # 번역 공급자 우선순위 결정
    providers = []
    if TRANSLATE_PROVIDER == "papago":
        providers = ["papago"]
    elif TRANSLATE_PROVIDER == "google":
        providers = ["google"]
    elif TRANSLATE_PROVIDER == "none":
        providers = []
    else:
        if PAPAGO_ID and PAPAGO_SECRET:
            providers.append("papago")
        if GOOGLE_KEY:
            providers.append("google")

    # 순차 시도
    for p in providers:
        try:
            func = try_papago if p == "papago" else try_google
            out = _retry(func)
            out = _postprocess_korean(out)
            _cache[key] = out
            return out
        except Exception as e:
            logger.warning("Translate provider '%s' failed: %s", p, e)

    # 폴백: 번역 실패 시 원문 반환
    return text
