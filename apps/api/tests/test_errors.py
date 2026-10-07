import pytest
from fastapi import APIRouter
from pydantic import BaseModel

from app.errors import ApiError
from app.main import create_app
from tests.conftest import assert_error_shape


class _Body(BaseModel):
    count: int


@pytest.fixture
def probe():
    """A throwaway app with routes that fail in each way the handlers cover."""
    from fastapi.testclient import TestClient

    router = APIRouter()

    @router.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    @router.get("/cooldown")
    def cooldown():
        details = {"retake_available_at": "2026-10-07T12:00:00Z"}
        raise ApiError(429, "rate_limited", "Try again later", details)

    @router.post("/echo")
    def echo(body: _Body):
        return body

    app = create_app()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def test_unknown_route_uses_error_shape(probe):
    res = probe.get("/v1/does-not-exist")
    assert res.status_code == 404
    assert_error_shape(res.json())
    assert res.json()["code"] == "not_found"


def test_wrong_method_uses_error_shape(probe):
    res = probe.delete("/health")
    assert res.status_code == 405
    assert_error_shape(res.json())


def test_validation_error_uses_error_shape_without_echoing_input(probe):
    res = probe.post("/echo", json={"count": "private-value"})
    assert res.status_code == 422
    body = res.json()
    assert_error_shape(body)
    assert body["code"] == "validation_error"
    assert body["details"]["errors"][0]["loc"] == ["body", "count"]
    assert "private-value" not in res.text


def test_api_error_carries_code_and_details(probe):
    res = probe.get("/cooldown")
    assert res.status_code == 429
    assert res.json() == {
        "code": "rate_limited",
        "message": "Try again later",
        "details": {"retake_available_at": "2026-10-07T12:00:00Z"},
    }


def test_unhandled_exception_hides_internals(probe):
    res = probe.get("/boom")
    assert res.status_code == 500
    assert_error_shape(res.json())
    assert res.json()["code"] == "internal_error"
    assert "secret internal detail" not in res.text
