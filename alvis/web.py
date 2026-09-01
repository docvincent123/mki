from __future__ import annotations

from html import unescape
from urllib.parse import urljoin, urlparse, quote_plus
from urllib.request import Request, urlopen
import re


class WebError(RuntimeError):
    pass


def _request(url: str, limit: int = 5_000_000):
    if not url.startswith(("https://", "http://")):
        raise WebError("Only http(s) URLs are supported")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ALVIS/2.0"})
    return urlopen(req, timeout=20), limit


def fetch_url(url: str) -> str:
    response, limit = _request(url)
    with response:
        raw = response.read(limit)
        content_type = response.headers.get_content_type()
    if content_type not in {"text/html", "text/plain", "application/json", "text/xml"}:
        raise WebError(f"Unsupported content type: {content_type}")
    text = raw.decode("utf-8", errors="replace")
    if content_type == "text/html":
        text = re.sub(r"(?is)<(script|style|noscript|svg).*?>.*?</\1>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()[:60_000]


def search_web(query: str, max_results: int = 8) -> str:
    """Return structured public search results rather than a raw search page."""
    max_results = max(1, min(int(max_results or 8), 12))
    url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
    response, _ = _request(url, 2_000_000)
    with response:
        html = response.read().decode("utf-8", errors="replace")
    results = []
    pattern = re.compile(r'<a[^>]*class=["\'][^"\']*result__a[^"\']*["\'][^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    for href, title in pattern.findall(html):
        title = re.sub(r"<[^>]+>", " ", unescape(title)).strip()
        href = unescape(href)
        # DuckDuckGo may wrap the destination in a redirect URL.
        m = re.search(r"uddg=([^&]+)", href)
        if m:
            from urllib.parse import unquote
            href = unquote(m.group(1))
        if urlparse(href).scheme in {"http", "https"} and title:
            results.append(f"{len(results)+1}. {title[:180]}\nURL: {href}")
        if len(results) >= max_results: break
    if not results:
        # Fallback to a readable search page when markup changes.
        return fetch_url(url)[:40_000]
    return "\n\n".join(results)


def extract_links(url: str) -> str:
    response, _ = _request(url, 3_000_000)
    with response:
        html = response.read().decode("utf-8", errors="replace")
    links = []
    for href, label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        label = re.sub(r"<[^>]+>", " ", unescape(label)).strip()
        full = urljoin(url, unescape(href))
        if urlparse(full).scheme in {"http", "https"} and label:
            links.append(f"{label[:120]} -> {full}")
        if len(links) >= 100: break
    return "\n".join(links)
