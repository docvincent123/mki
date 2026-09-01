from __future__ import annotations

from html import unescape
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import re


class WebError(RuntimeError):
    pass


def fetch_url(url: str) -> str:
    if not url.startswith(("https://", "http://")):
        raise WebError("Only http(s) URLs are supported")
    req = Request(url, headers={"User-Agent": "ALVIS/1.0"})
    with urlopen(req, timeout=15) as response:
        raw = response.read(5_000_000)
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "text/plain", "application/json", "text/xml"}:
            raise WebError(f"Unsupported content type: {content_type}")
    text = raw.decode("utf-8", errors="replace")
    if content_type == "text/html":
        text = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:60_000]


def search_web(query: str, max_results: int = 6) -> str:
    # Lightweight public search endpoint; no browser automation required.
    from urllib.parse import quote_plus
    url = "https://www.google.com/search?q=" + quote_plus(query)
    text = fetch_url(url)
    return text[:40_000]


def extract_links(url: str) -> str:
    req = Request(url, headers={"User-Agent": "ALVIS/1.0"})
    with urlopen(req, timeout=15) as response:
        html = response.read(3_000_000).decode("utf-8", errors="replace")
    links = []
    for href, label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        label = re.sub(r"<[^>]+>", " ", unescape(label)).strip()
        full = urljoin(url, href)
        if urlparse(full).scheme in {"http", "https"} and label:
            links.append(f"{label[:120]} -> {full}")
        if len(links) >= 100: break
    return "\n".join(links)
