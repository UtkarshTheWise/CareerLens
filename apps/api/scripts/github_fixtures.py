"""Record real GitHub responses once, replay them offline in tests.

A fixture is one JSON file per request, named by `request_fingerprint(method, url, body)`, holding the
status and parsed body. Request headers (and so the token) are never stored.
"""

import json
from pathlib import Path

import httpx

from app.services.github import request_fingerprint

FIXTURE_ROOT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "github"


def _request_body(request: httpx.Request) -> object:
    return json.loads(request.content) if request.content else None


def _fingerprint(request: httpx.Request) -> str:
    return request_fingerprint(request.method, str(request.url), _request_body(request))


class RecordingTransport(httpx.BaseTransport):
    """Forwards to the real transport and writes every response under `out_dir`."""

    def __init__(self, inner: httpx.BaseTransport, out_dir: Path):
        self.inner = inner
        self.out_dir = out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self.inner.handle_request(request)
        response.read()
        try:
            body = json.loads(response.content) if response.content else None
        except ValueError:
            body = None
        sent = _request_body(request)
        summary = None
        if isinstance(sent, dict):
            summary = {
                "query": str(sent.get("query", "")).strip().split("\n")[0][:80],
                "variables": sent.get("variables"),
            }
        entry = {
            "method": request.method,
            "url": str(request.url),
            "request": summary,
            "status": response.status_code,
            "body": body,
        }
        path = self.out_dir / f"{_fingerprint(request)[:20]}.json"
        path.write_text(json.dumps(entry, indent=1, ensure_ascii=False), encoding="utf-8")
        return httpx.Response(
            response.status_code,
            content=response.content,
            headers={"content-type": response.headers.get("content-type", "application/json")},
            request=request,
        )


class ReplayTransport(httpx.BaseTransport):
    """Answers requests from recorded files. An unrecorded request fails the test loudly."""

    def __init__(self, directory: Path):
        self.entries: dict[str, dict] = {}
        self.requests = 0
        for file in sorted(directory.glob("*.json")):
            entry = json.loads(file.read_text(encoding="utf-8"))
            self.entries[file.stem] = entry

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests += 1
        entry = self.entries.get(_fingerprint(request)[:20])
        if entry is None:
            sent = _request_body(request)
            variables = sent.get("variables") if isinstance(sent, dict) else None
            raise AssertionError(
                f"no recorded response for {request.method} {request.url} variables={variables}"
            )
        body = entry["body"]
        content = json.dumps(body).encode("utf-8") if body is not None else b""
        return httpx.Response(
            entry["status"], content=content, headers={"content-type": "application/json"}, request=request
        )
