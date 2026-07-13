from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def source_timestamp_url(source_url: str, timestamp_ms: int) -> str:
    """Return the original public URL with a best-effort jump to the reference time."""
    seconds = max(0, timestamp_ms // 1000)
    parsed = urlparse(source_url)
    host = parsed.netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        query = [(key, value) for key, value in parse_qsl(parsed.query) if key != "t"]
        query.append(("t", f"{seconds}s"))
        return urlunparse(parsed._replace(query=urlencode(query)))
    if "bilibili.com" in host:
        query = [(key, value) for key, value in parse_qsl(parsed.query) if key != "t"]
        query.append(("t", str(seconds)))
        return urlunparse(parsed._replace(query=urlencode(query)))
    return urlunparse(parsed._replace(fragment=f"t={seconds}"))
