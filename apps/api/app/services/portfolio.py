"""Fetch a student's portfolio page and reduce it to text for the design judge (docs/PIPELINE.md 5b).

The URL is supplied by a user and fetched from our server, so this is an SSRF surface. Defences:
http/https on ports 80/443 only, no credentials in the URL, every resolved address must be a public
one (loopback, private, link-local such as the cloud metadata address, multicast and reserved ranges
are refused), redirects are followed by hand (max 3) and re-checked at every hop, the body is capped
at 1 MB, only HTML is accepted, and requests time out at 10 s.

Residual risk: the name is resolved once for the check and again by the HTTP client, so a hostile DNS
server could answer differently the second time (DNS rebinding). Acceptable for the prototype; the
fix is to connect to the vetted IP directly.
"""

import ipaddress
import logging
import socket
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx
from sqlalchemy.orm import Session

from app.services.cache import cache_get, cache_set
from app.services.github import request_fingerprint

logger = logging.getLogger("careerlens.portfolio")

MAX_BYTES = 1_000_000
MAX_REDIRECTS = 3
TIMEOUT_S = 10.0
MAX_TEXT_CHARS = 3000
MIN_USEFUL_CHARS = 80
CACHE_TTL = timedelta(hours=24)
ALLOWED_PORTS = {None, 80, 443}
HTML_TYPES = ("text/html", "application/xhtml+xml")

Resolver = Callable[[str], list[str]]


class UnsafeUrl(ValueError):
    """The link points somewhere we must not fetch from."""


@dataclass
class PageText:
    url: str
    readable: bool
    title: str = ""
    description: str = ""
    text: str = ""
    reason: str | None = None  # why it is not readable


def default_resolver(host: str) -> list[str]:
    return sorted({info[4][0] for info in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)})


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%")[0])  # drop an IPv6 zone id
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped  # ::ffff:127.0.0.1 is loopback in disguise
    return ip.is_global and not ip.is_multicast


def check_url(url: str, resolver: Resolver = default_resolver) -> None:
    """Raise UnsafeUrl unless the URL may be fetched. Always checks the resolved addresses."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise UnsafeUrl("only http and https links are fetched")
    if not parts.hostname:
        raise UnsafeUrl("the link has no host")
    if parts.username or parts.password:
        raise UnsafeUrl("links with credentials are not fetched")
    try:
        port = parts.port
    except ValueError as exc:
        raise UnsafeUrl("the link has an invalid port") from exc
    if port not in ALLOWED_PORTS:
        raise UnsafeUrl("only the standard web ports are fetched")
    try:
        addresses = [str(ipaddress.ip_address(parts.hostname))]  # an IP literal
    except ValueError:
        try:
            addresses = resolver(parts.hostname)
        except (OSError, ValueError) as exc:  # ValueError covers UnicodeError for empty or over-long labels
            raise UnsafeUrl("the host name could not be resolved") from exc
    if not addresses:
        raise UnsafeUrl("the host name could not be resolved")
    if not all(_is_public(a) for a in addresses):
        raise UnsafeUrl("the link points to a non-public address")


# ---------------------------------------------------------------- HTML -> text


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg", "head", "template", "iframe"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.chunks: list[str] = []
        self.meta: dict[str, str] = {}
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            if key in ("og:title", "og:description", "description") and values.get("content"):
                self.meta.setdefault(key, values["content"] or "")
        elif tag in self._SKIP and tag != "head":
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag in self._SKIP and tag != "head" and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        elif not self._skip_depth and data.strip():
            self.chunks.append(data.strip())


def extract_text(url: str, html: str) -> PageText:
    parser = _TextExtractor()
    parser.feed(html)
    title = " ".join(" ".join(parser.title_parts).split()) or parser.meta.get("og:title", "")
    text = " ".join(" ".join(parser.chunks).split())[:MAX_TEXT_CHARS]
    description = parser.meta.get("og:description") or parser.meta.get("description", "")
    page = PageText(url=url, readable=True, title=title[:200], description=description[:500], text=text)
    if len(text) < MIN_USEFUL_CHARS and not description:
        page.readable = False
        page.reason = "the page has no readable text (it may need JavaScript to display)"
    return page


# ---------------------------------------------------------------- fetching


def _fetch(url: str, resolver: Resolver, transport: httpx.BaseTransport | None) -> PageText:
    headers = {"User-Agent": "careerlens-portfolio-reader/0.2", "Accept": "text/html,application/xhtml+xml"}
    current = url
    with httpx.Client(
        transport=transport, timeout=TIMEOUT_S, follow_redirects=False, headers=headers
    ) as client:
        for _ in range(MAX_REDIRECTS + 1):
            try:
                check_url(current, resolver)
            except UnsafeUrl as exc:
                return PageText(url=url, readable=False, reason=str(exc))
            try:
                with client.stream("GET", current) as response:
                    if response.is_redirect and response.headers.get("location"):
                        current = urljoin(current, response.headers["location"])
                        continue
                    if response.status_code >= 400:
                        return PageText(
                            url=url, readable=False, reason=f"the page answered HTTP {response.status_code}"
                        )
                    kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    if kind not in HTML_TYPES:
                        return PageText(url=url, readable=False, reason="the link is not a web page")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body += chunk
                        if len(body) > MAX_BYTES:
                            return PageText(url=url, readable=False, reason="the page is too large to read")
                    html = bytes(body).decode(response.encoding or "utf-8", errors="replace")
            except httpx.HTTPError as exc:
                logger.info("portfolio fetch failed: %s", type(exc).__name__)
                return PageText(url=url, readable=False, reason="the page could not be reached")
            return extract_text(url, html)
    return PageText(url=url, readable=False, reason="the link redirects too many times")


def fetch_page(
    url: str,
    db: Session | None = None,
    *,
    resolver: Resolver = default_resolver,
    transport: httpx.BaseTransport | None = None,
    refresh: bool = False,
) -> PageText:
    """Safely fetch a portfolio page. Readable results are cached for 24 h; failures never are."""
    key = request_fingerprint("GET", f"page:{url}")
    if db is not None and not refresh:
        cached = cache_get(db, key)
        if cached is not None:
            return PageText(**cached)
    page = _fetch(url, resolver, transport)
    if db is not None and page.readable:
        cache_set(db, key, "http", asdict(page), CACHE_TTL)
    return page
