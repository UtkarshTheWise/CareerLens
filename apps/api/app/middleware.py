"""Two small ASGI middlewares: a request body size limit and a one-line-per-request log.

Both are plain ASGI (not BaseHTTPMiddleware) so they never buffer a body or interfere with background tasks.
Neither ever logs a body, a query string, a header or a token.
"""

import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

logger = logging.getLogger("careerlens.request")

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]

BODY_METHODS = {"POST", "PUT", "PATCH"}
UPLOAD_PATH = re.compile(r"^/v1/profiles/[^/]+/documents/?$")
REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


DRAIN_MAX_BYTES = 32 * 1024 * 1024  # how much of a refused body is read and thrown away before replying


class _TooLarge(Exception):
    pass


async def _drain(receive: Receive, budget: int = DRAIN_MAX_BYTES) -> None:
    """Read and discard the rest of a refused body. Replying while the client is still sending makes the
    connection reset, and the browser then reports a network error instead of our 413."""
    while budget > 0:
        message = await receive()
        if message["type"] != "http.request" or not message.get("more_body", False):
            return
        budget -= len(message.get("body", b""))


def _json(status: int, body: dict[str, Any], extra: list[tuple[bytes, bytes]] | None = None) -> list[Message]:
    payload = json.dumps(body).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(payload)).encode())]
    return [
        {"type": "http.response.start", "status": status, "headers": [*headers, *(extra or [])]},
        {"type": "http.response.body", "body": payload},
    ]


class BodySizeLimitMiddleware:
    """413 in the contract's Error shape when a request body is bigger than allowed.

    A declared Content-Length is checked up front; a body sent without one (chunked) is counted as it
    streams. Whatever the app tries to answer once the limit was crossed is replaced by the 413.
    """

    def __init__(self, app: Callable[..., Awaitable[None]], *, max_bytes: int, max_upload_bytes: int):
        self.app = app
        self.max_bytes = max_bytes
        self.max_upload_bytes = max_upload_bytes

    def _limit_for(self, scope: Scope) -> int:
        return self.max_upload_bytes if UPLOAD_PATH.match(scope.get("path", "")) else self.max_bytes

    def _too_large(self, limit: int) -> list[Message]:
        body = {
            "code": "payload_too_large",
            "message": f"The request is larger than the {limit // 1024} KB allowed here",
            "details": {"max_bytes": limit},
        }
        return _json(413, body)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in BODY_METHODS:
            await self.app(scope, receive, send)
            return
        limit = self._limit_for(scope)
        declared = dict(scope.get("headers", [])).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await _drain(receive)
            for message in self._too_large(limit):
                await send(message)
            return

        seen = 0
        exceeded = False
        started = False

        async def limited_receive() -> Message:
            nonlocal seen, exceeded
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > limit:
                    exceeded = True
                    raise _TooLarge
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal started
            if not exceeded:
                await send(message)
                return
            if not started:  # replace whatever the app answered (usually a 400/500 about the cut-off body)
                started = True
                for replacement in self._too_large(limit):
                    await send(replacement)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _TooLarge:
            await _drain(receive)
            if not started:
                for message in self._too_large(limit):
                    await send(message)


class RequestLogMiddleware:
    """One log line per request: id, method, route template, status and duration. Sets X-Request-ID."""

    def __init__(self, app: Callable[..., Awaitable[None]]):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope.get("headers", [])).get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if REQUEST_ID.match(incoming) else uuid.uuid4().hex[:16]
        started = time.perf_counter()
        status = 500

        async def logging_send(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message = {
                    **message,
                    "headers": [*message.get("headers", []), (b"x-request-id", request_id.encode())],
                }
            await send(message)

        try:
            await self.app(scope, receive, logging_send)
        finally:
            route = scope.get("route")
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": scope.get("method"),
                    "route": getattr(route, "path", "unmatched"),  # the template: never the query string
                    "status": status,
                    "ms": int((time.perf_counter() - started) * 1000),
                },
            )
