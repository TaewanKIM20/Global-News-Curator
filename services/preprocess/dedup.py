import re
import hashlib
from typing import Iterable

_TOKEN_RX = re.compile(r"[A-Za-z0-9가-힣]+")

def _tokens(s: str) -> list[str]:
    return _TOKEN_RX.findall((s or "").lower())

def _shingles(tokens: list[str], k: int = 3) -> Iterable[str]:
    if len(tokens) < k:
        yield " ".join(tokens)  # 너무 짧으면 통째로
        return
    for i in range(len(tokens) - k + 1):
        yield " ".join(tokens[i:i+k])

def _feature_hash(s: str) -> int:
    h = hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "big", signed=False)

def simhash64(text: str, title: str | None = None) -> int:
    tokens = _tokens(text)
    if not tokens:
        return 0

    bits = [0]*64

    # 3-gram shingle 가중치 1
    for g in _shingles(tokens, k=3):
        hv = _feature_hash(g)
        for i in range(64):
            bits[i] += 1 if ((hv >> i) & 1) else -1

    # 제목 토큰은 가중치 2
    if title:
        for tk in _tokens(title):
            hv = _feature_hash(tk)
            for i in range(64):
                bits[i] += 2 if ((hv >> i) & 1) else -2

    v = 0
    for i in range(64):
        if bits[i] >= 0:
            v |= (1 << i)
    return v

def hamming_distance64(a: int, b: int) -> int:
    return (a ^ b).bit_count()

def _adaptive_threshold(char_len: int) -> int:
    # 길수록 임계값 경감(더 빡빡)
    if char_len >= 4000:
        return 5
    if char_len >= 2000:
        return 6
    if char_len >= 1000:
        return 7
    return 8  # 짧은 문서는 관대

def is_near_duplicate(hash_a: int, hash_b: int, char_len: int | None = None, base_threshold: int | None = None) -> bool:
    if hash_a == 0 or hash_b == 0:
        return False
    thr = base_threshold if base_threshold is not None else _adaptive_threshold(char_len or 0)
    return hamming_distance64(hash_a, hash_b) <= thr
