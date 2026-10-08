import json
import logging
from pathlib import Path

import pytest

from app.logging_config import JsonFormatter, configure_logging
from tests.conftest import assert_error_shape

FIXTURES = Path(__file__).parent / "fixtures"
KB = 1024


def profile(client) -> str:
    return client.post("/v1/profiles", json={"name": "Priya Raman"}).json()["id"]


# ---------------------------------------------------------------- body size limit


def test_a_big_json_body_is_413_in_the_error_shape(client):
    res = client.post(
        "/v1/profiles",
        content=b'{"name": "' + b"x" * (1100 * KB) + b'"}',
        headers={"content-type": "application/json"},
    )
    assert res.status_code == 413
    assert res.json()["code"] == "payload_too_large" and res.json()["details"] == {"max_bytes": 1024 * KB}
    assert_error_shape(res.json())


def test_the_limit_applies_without_a_content_length_too(client):
    def chunks():
        for _ in range(3):
            yield b"x" * (600 * KB)  # chunked transfer encoding: no Content-Length to check up front

    res = client.post("/v1/profiles", content=chunks(), headers={"content-type": "application/json"})
    assert res.status_code == 413 and res.json()["code"] == "payload_too_large"


def test_a_413_still_carries_cors_headers_and_a_request_id(client):
    res = client.post(
        "/v1/profiles", content=b"x" * (1100 * KB),
        headers={"content-type": "application/json", "origin": "http://localhost:3000"},
    )  # fmt: skip
    assert res.status_code == 413
    assert res.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert res.headers["x-request-id"]


def test_normal_requests_and_gets_are_untouched(client):
    pid = profile(client)
    assert client.get(f"/v1/profiles/{pid}").status_code == 200
    ok = client.patch(f"/v1/profiles/{pid}", json={"department": "CSE"})
    assert ok.status_code == 200


def test_uploads_get_the_larger_limit_and_the_files_own_5mb_rule_still_applies(client):
    pid = profile(client)
    small = client.post(
        f"/v1/profiles/{pid}/documents", data={"kind": "resume"},
        files={"file": ("resume.pdf", (FIXTURES / "resume.pdf").read_bytes())},
    )  # fmt: skip
    assert small.status_code == 200
    medium = client.post(
        f"/v1/profiles/{pid}/documents", data={"kind": "resume"},
        files={"file": ("big.pdf", b"%PDF-1.4 " + b"0" * (5500 * KB))},
    )  # fmt: skip
    assert medium.status_code == 413 and medium.json()["message"] == "File is larger than 5 MB"
    huge = client.post(
        f"/v1/profiles/{pid}/documents", data={"kind": "resume"},
        files={"file": ("huge.pdf", b"%PDF-1.4 " + b"0" * (7000 * KB))},
    )  # fmt: skip
    assert huge.status_code == 413 and huge.json()["details"] == {"max_bytes": 6144 * KB}


# ---------------------------------------------------------------- request log


def request_records(caplog) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "careerlens.request"]


def test_every_request_is_logged_once_with_the_route_template(client, caplog):
    caplog.set_level(logging.INFO)
    pid = profile(client)
    caplog.clear()
    res = client.get(f"/v1/profiles/{pid}")
    [record] = request_records(caplog)
    assert (record.method, record.route, record.status) == ("GET", "/v1/profiles/{profile_id}", 200)
    assert record.request_id == res.headers["x-request-id"] and isinstance(record.ms, int)


def test_the_log_never_holds_query_strings_bodies_or_headers(client, caplog):
    caplog.set_level(logging.DEBUG)
    client.get(
        "/v1/applications",
        params={"profile_id": profile(client), "secret": "hunter2"},
        headers={"x-api-key": "k-123"},
    )
    client.post("/v1/profiles", json={"name": "Distinctive Student Name"})
    text = " ".join(f"{r.getMessage()} {r.__dict__}" for r in caplog.records)
    assert "hunter2" not in text and "k-123" not in text and "Distinctive Student Name" not in text


def test_an_unknown_path_is_logged_as_unmatched(client, caplog):
    caplog.set_level(logging.INFO)
    assert client.get("/nope").status_code == 404
    assert request_records(caplog)[-1].route == "unmatched" and request_records(caplog)[-1].status == 404


def test_a_valid_incoming_request_id_is_kept_and_a_bad_one_replaced(client):
    assert (
        client.get("/health", headers={"x-request-id": "abc12345-trace"}).headers["x-request-id"]
        == "abc12345-trace"
    )
    bad = client.get("/health", headers={"x-request-id": "bad id\twith spaces"}).headers["x-request-id"]
    assert bad != "bad id\twith spaces" and len(bad) == 16


def test_uploading_a_resume_does_not_put_its_text_in_the_logs(client, caplog):
    from app.services.ingest import extract_text

    data = (FIXTURES / "resume.pdf").read_bytes()
    words = [w for w in extract_text("resume.pdf", data).text.split() if len(w) > 6][:5]
    caplog.set_level(logging.DEBUG)
    client.post(
        f"/v1/profiles/{profile(client)}/documents",
        data={"kind": "resume"},
        files={"file": ("resume.pdf", data)},
    )
    text = " ".join(r.getMessage() for r in caplog.records)
    assert words and not any(w in text for w in words)


# ---------------------------------------------------------------- formats


def record(msg="hello", **extra) -> logging.LogRecord:
    r = logging.LogRecord("careerlens.test", logging.INFO, __file__, 1, msg, (), None)
    r.__dict__.update(extra)
    return r


def test_json_lines_carry_extras_and_parse():
    line = JsonFormatter().format(record("request", request_id="abc", status=200))
    data = json.loads(line)
    assert data["msg"] == "request" and data["logger"] == "careerlens.test" and data["level"] == "INFO"
    assert data["request_id"] == "abc" and data["status"] == 200 and data["ts"].endswith("+00:00")


def test_exceptions_are_included_in_json_lines():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        r = record("failed")
        r.exc_info = sys.exc_info()
    assert "ValueError: boom" in json.loads(JsonFormatter().format(r))["exc"]


@pytest.mark.parametrize("fmt", ["json", "text"])
def test_configure_logging_is_idempotent(fmt):
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        configure_logging("WARNING", fmt)
        configure_logging("WARNING", fmt)
        ours = [h for h in root.handlers if getattr(h, "_careerlens_handler", False)]
        assert len(ours) == 1 and root.level == logging.WARNING
    finally:
        configure_logging("INFO", "json")
        root.handlers = [h for h in root.handlers if h in before or getattr(h, "_careerlens_handler", False)]
