# services/translate/translate.py
import os, time, json, requests, logging
from typing import Optional

logger = logging.getLogger(__name__)

PAPAGO_ID = os.getenv("PAPAGO_CLIENT_ID")
PAPAGO_SECRET = os.getenv("PAPAGO_CLIENT_SECRET")
GOOGLE_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY")
TRANSLATE_PROVIDER = os.getenv("TRANSLATE_PROVIDER", "auto")  # auto|papago|google|none

_cache: dict[tuple[str,str], str] = {}

def _retry(func, tries=3, backoff=1.5):
    for i in range(tries):
        try:
            return func()
        except Exception as e:
            if i == tries-1:
                raise
            time.sleep(backoff ** i)

def translate_to_ko(text: str, source_lang: Optional[str] = None) -> str:
    if not text:
        return text
    key = (text[:4000], source_lang or "auto")
    if key in _cache:
        return _cache[key]

    def try_papago():
        url = "https://openapi.naver.com/v1/papago/n2mt"
        headers = {"X-Naver-Client-Id": PAPAGO_ID, "X-Naver-Client-Secret": PAPAGO_SECRET}
        data = {"source": source_lang or "auto", "target": "ko", "text": text[:4900]}
        r = requests.post(url, headers=headers, data=data, timeout=15)
        r.raise_for_status()
        return r.json()["message"]["result"]["translatedText"]

    def try_google():
        url = f"https://translation.googleapis.com/language/translate/v2?key={GOOGLE_KEY}"
        payload = {"q": text[:4900], "target": "ko"}
        if source_lang: payload["source"] = source_lang
        r = requests.post(url, json=payload, timeout=15)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            # 핵심: 403/429 등은 폴백
            status = getattr(e.response, "status_code", None)
            logger.warning("Google Translate error status=%s", status)
            raise
        return r.json()["data"]["translations"][0]["translatedText"]

    # 우선순위 결정
    providers = []
    if TRANSLATE_PROVIDER == "papago":
        providers = ["papago"]
    elif TRANSLATE_PROVIDER == "google":
        providers = ["google"]
    elif TRANSLATE_PROVIDER == "none":
        providers = []
    else:
        # auto: Papago가 있으면 Papago → 없으면 Google → 없으면 none
        if PAPAGO_ID and PAPAGO_SECRET:
            providers.append("papago")
        if GOOGLE_KEY:
            providers.append("google")

    for p in providers:
        try:
            out = _retry(try_papago if p == "papago" else try_google)
            _cache[key] = out
            return out
        except Exception as e:
            logger.warning("Translate provider '%s' failed: %s", p, e)

    # 마지막 폴백: 번역 없이 원문 반환 (파이프라인을 멈추지 않음)
    return text
