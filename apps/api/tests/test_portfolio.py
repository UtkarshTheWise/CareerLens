import httpx
import pytest

from app.db.base import SessionLocal
from app.db.models import CacheEntry
from app.services.portfolio import (
    MAX_BYTES,
    MAX_TEXT_CHARS,
    UnsafeUrl,
    check_url,
    extract_text,
    fetch_page,
)

PUBLIC_IP = "93.184.216.34"
HOSTS = {
    "portfolio.example.dev": [PUBLIC_IP],
    "other.example.dev": ["8.8.8.8"],
    "evil.example.dev": ["10.0.0.5"],
    "mixed.example.dev": [PUBLIC_IP, "127.0.0.1"],
    "ipv6.example.dev": ["2606:2800:220:1:248:1893:25c8:1946"],
    "decimal.example.dev": ["127.0.0.1"],
    "mapped.example.dev": ["::ffff:127.0.0.1"],
}


def resolver(host: str) -> list[str]:
    if host not in HOSTS:
        raise OSError("no such host")
    return HOSTS[host]


HTML = """<html><head><title>  Transit app   case study </title>
<meta property="og:title" content="Transit app">
<meta property="og:description" content="Redesigning bus tickets for commuters">
<style>.x{color:red}</style><script>var secret = "do not read me";</script></head>
<body><h1>Problem</h1><p>Commuters waste time at ticket counters.</p>
<script>alert(1)</script><p>Research: 12 interviews and 3 rounds of wireframes in Figma. {filler}</p>
<noscript>enable javascript</noscript></body></html>""".replace("{filler}", "More detail. " * 20)


def page_transport(body=HTML, status=200, content_type="text/html; charset=utf-8", calls=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(str(request.url))
        return httpx.Response(status, content=body, headers={"content-type": content_type})

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------- the address check


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/",
        "http://127.0.0.1/",
        "http://127.0.0.1:80/admin",
        "http://[::1]/",
        "http://10.1.2.3/",
        "http://192.168.0.10/",
        "http://172.16.5.5/",
        "http://169.254.169.254/latest/meta-data/",
        "http://0.0.0.0/",
        "http://100.64.0.1/",
        "http://evil.example.dev/",  # name resolving to a private address
        "http://mixed.example.dev/",  # one bad address among good ones
        "http://decimal.example.dev/",
        "http://mapped.example.dev/",  # ::ffff:127.0.0.1
        "file:///etc/passwd",
        "ftp://portfolio.example.dev/",
        "gopher://portfolio.example.dev/",
        "javascript:alert(1)",
        "http://user:pass@portfolio.example.dev/",
        "http://portfolio.example.dev:6379/",
        "http://portfolio.example.dev:22/",
        "http:///nohost",
        "http://nxdomain.example.dev/",
    ],
)
def test_unsafe_urls_are_refused(url):
    with pytest.raises(UnsafeUrl):
        check_url(url, resolver)


@pytest.mark.parametrize(
    "url",
    [
        "https://portfolio.example.dev/case-study",
        "http://other.example.dev/",
        "https://portfolio.example.dev:443/x",
        "https://ipv6.example.dev/",
        "http://93.184.216.34/",
    ],
)
def test_public_urls_are_allowed(url):
    check_url(url, resolver)


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1/", "http://169.254.169.254/", "http://evil.example.dev/", "file:///etc/passwd"]
)
def test_refused_urls_never_reach_the_network(url):
    calls: list[str] = []
    page = fetch_page(url, resolver=resolver, transport=page_transport(calls=calls))
    assert page.readable is False and page.reason and calls == []


def test_a_redirect_to_a_private_address_is_stopped_at_that_hop():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.host == "portfolio.example.dev":
            return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"})
        return httpx.Response(200, content="secret", headers={"content-type": "text/html"})

    page = fetch_page(
        "https://portfolio.example.dev/", resolver=resolver, transport=httpx.MockTransport(handler)
    )
    assert page.readable is False and "non-public" in page.reason
    assert seen == ["https://portfolio.example.dev/"]  # the metadata address was never requested


def test_redirects_are_followed_up_to_three_hops():
    def handler(request: httpx.Request) -> httpx.Response:
        hop = int(request.url.params.get("n", "0"))
        if hop < 3:
            return httpx.Response(302, headers={"location": f"/next?n={hop + 1}"})
        return httpx.Response(200, content=HTML, headers={"content-type": "text/html"})

    ok = fetch_page(
        "https://portfolio.example.dev/?n=0", resolver=resolver, transport=httpx.MockTransport(handler)
    )
    assert ok.readable and ok.title == "Transit app case study"

    def forever(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "/again"})

    loop = fetch_page(
        "https://portfolio.example.dev/", resolver=resolver, transport=httpx.MockTransport(forever)
    )
    assert loop.readable is False and "redirects too many times" in loop.reason


# ---------------------------------------------------------------- fetching limits


def test_non_html_error_status_oversize_and_network_failures_are_unreadable():
    def fetch(**kw):
        return fetch_page("https://portfolio.example.dev/", resolver=resolver, transport=page_transport(**kw))

    assert "not a web page" in fetch(content_type="application/pdf").reason
    assert "HTTP 404" in fetch(status=404).reason
    assert "too large" in fetch(body=b"<p>" + b"x" * (MAX_BYTES + 10)).reason

    def boom(request):
        raise httpx.ConnectTimeout("slow")

    page = fetch_page(
        "https://portfolio.example.dev/", resolver=resolver, transport=httpx.MockTransport(boom)
    )
    assert page.readable is False and "could not be reached" in page.reason


# ---------------------------------------------------------------- text extraction


def test_extraction_keeps_visible_text_and_metadata_only():
    page = extract_text("https://x.dev", HTML)
    assert page.readable and page.title == "Transit app case study"
    assert page.description == "Redesigning bus tickets for commuters"
    assert "Commuters waste time at ticket counters." in page.text and "12 interviews" in page.text
    for hidden in ("do not read me", "alert(1)", "color:red", "enable javascript"):
        assert hidden not in page.text
    assert len(page.text) <= MAX_TEXT_CHARS


def test_long_pages_are_cut_to_3000_chars():
    page = extract_text("https://x.dev", "<p>" + "word " * 2000 + "</p>")
    assert len(page.text) == MAX_TEXT_CHARS


def test_pages_that_need_javascript_are_not_readable():
    page = extract_text(
        "https://x.dev",
        "<html><head><title>My work</title></head><body><div id='root'></div><script>app()</script></body></html>",
    )
    assert page.readable is False and "JavaScript" in page.reason and page.title == "My work"
    assert extract_text(
        "https://x.dev", "<body><div></div><meta name='description' content='A designer portfolio'></body>"
    ).readable


# ---------------------------------------------------------------- cache


def test_readable_pages_are_cached_and_failures_are_not():
    calls: list[str] = []
    with SessionLocal() as db:
        first = fetch_page(
            "https://portfolio.example.dev/", db, resolver=resolver, transport=page_transport(calls=calls)
        )
        again = fetch_page(
            "https://portfolio.example.dev/", db, resolver=resolver, transport=page_transport(calls=calls)
        )
        assert first == again and len(calls) == 1
        assert db.query(CacheEntry).one().kind == "http"
        fetch_page(
            "https://portfolio.example.dev/",
            db,
            resolver=resolver,
            transport=page_transport(calls=calls),
            refresh=True,
        )
        assert len(calls) == 2

        fetch_page(
            "https://other.example.dev/",
            db,
            resolver=resolver,
            transport=page_transport(status=500, calls=calls),
        )
        fetch_page(
            "https://other.example.dev/",
            db,
            resolver=resolver,
            transport=page_transport(status=500, calls=calls),
        )
        assert len(calls) == 4  # the failure was fetched twice, so it was not cached


def test_a_malformed_host_is_unsafe_not_a_crash():
    """getaddrinfo raises UnicodeError for empty or over-long DNS labels; one bad link must not fail an analysis."""
    from app.services.portfolio import UnsafeUrl, check_url, fetch_page

    for url in ("http://exa..mple.com/", "http://" + "a" * 70 + ".com/", "http://.example.com/"):
        with pytest.raises(UnsafeUrl):
            check_url(url)
    page = fetch_page("http://exa..mple.com/")
    assert page.readable is False
