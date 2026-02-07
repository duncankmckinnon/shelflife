import hashlib
import re


def _normalize(value: str | int) -> str:
    s = str(value).lower()
    s = re.sub(r"[^a-z0-9]", "", s)
    if len(s) > 50:
        s = s[:50]
    return s


def make_id(*parts: str | int) -> int:
    key = ":".join(_normalize(p) for p in parts)
    return int(hashlib.sha256(key.encode()).hexdigest()[:15], 16)
