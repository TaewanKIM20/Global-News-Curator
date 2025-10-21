import re
import hashlib

def _tokenize(s: str) -> list[str]:
    # 알파벳/숫자 단어 기준 토큰화 (간단)
    return re.findall(r"[A-Za-z0-9가-힣]+", (s or "").lower())

def _feature_hash(token: str) -> int:
    # 64-bit hash
    h = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "big", signed=False)

def simhash64(text: str, weight: int = 1) -> int:
    # 기본 simhash: 각 비트 가중합 → 부호로 비트 결정
    tokens = _tokenize(text)
    if not tokens:
        return 0
    bits = [0]*64
    for tk in tokens:
        h = _feature_hash(tk)
        for i in range(64):
            bits[i] += weight if (h >> i) & 1 else -weight
    v = 0
    for i in range(64):
        if bits[i] >= 0:
            v |= (1 << i)
    return v

def hamming_distance64(a: int, b: int) -> int:
    return (a ^ b).bit_count()

# 유사 판정: 해밍 거리 임계값(예: 8 이하이면 중복으로 간주)
def is_near_duplicate(hash_a: int, hash_b: int, threshold: int = 8) -> bool:
    if a_is_zero := (hash_a == 0) or (hash_b == 0):
        return False
    return hamming_distance64(hash_a, hash_b) <= threshold
