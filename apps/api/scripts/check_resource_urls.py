"""Request every URL in data/resources.yaml once and report the ones that don't answer.

    uv run python scripts/check_resource_urls.py

Live network; run by hand after editing resources.yaml. Not part of pytest (tests stay offline).
Exits 1 if any URL fails. 401/403/429 are reported as "blocked" (the site refuses scripts, which
says nothing about whether the page exists) and do not fail the run; open those in a browser.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

API_DIR = Path(__file__).resolve().parent.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.catalogue import load_resources  # noqa: E402

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
BLOCKED = {401, 403, 429}


def fetch(url: str) -> tuple[int | None, str]:
    try:
        with httpx.Client(follow_redirects=True, timeout=25, headers=HEADERS) as client:
            res = client.get(url)
        return res.status_code, str(res.url)
    except httpx.HTTPError as exc:
        return None, type(exc).__name__


def main() -> int:
    resources = load_resources()
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda r: fetch(r.url), resources))

    failed = blocked = 0
    for res, (status, final) in zip(resources, results, strict=True):
        if status is not None and status < 400:
            if final.rstrip("/") != res.url.rstrip("/"):
                print(f"moved    {res.id}: {res.url} -> {final}")
            continue
        if status in BLOCKED:
            blocked += 1
            print(f"blocked  {res.id}: HTTP {status} {res.url}")
        else:
            failed += 1
            print(f"FAILED   {res.id}: {status or final} {res.url}")
    print(
        f"{len(resources)} urls: {len(resources) - failed - blocked} ok, {blocked} blocked, {failed} failed"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
