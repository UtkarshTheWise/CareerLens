"""A small per-user limit on the operations that spend shared free-tier quota (LLM calls, GitHub calls).

One signed-in user could otherwise start analyses and quizzes in a loop and use up the Gemini, Groq and
GitHub allowances for everyone. The window is the last hour, kept in memory: the service runs as a single
process (see apps/api/README.md), so no shared store is needed. A limit of 0 turns a bucket off. The
DEV_AUTH user is exempt: in development everyone is that one pretend user.
"""

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Depends

from app.config import Settings, get_settings
from app.deps import DEV_SUBJECT, AuthContext, get_auth_context
from app.errors import ApiError

WINDOW_S = 3600.0

_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = threading.Lock()
clock: Callable[[], float] = time.monotonic  # tests replace it


def reset() -> None:
    with _lock:
        _hits.clear()


def check(bucket: str, subject: str, limit: int) -> None:
    """Record one use of `bucket` by `subject`; raise 429 if that makes more than `limit` in the last hour."""
    if limit <= 0 or subject == DEV_SUBJECT:
        return
    now = clock()
    with _lock:
        hits = _hits[(bucket, subject)]
        while hits and now - hits[0] >= WINDOW_S:
            hits.popleft()
        if len(hits) >= limit:
            wait = int(WINDOW_S - (now - hits[0])) + 1
            raise ApiError(
                429,
                "rate_limited",
                "You have used this a lot in the last hour. Try again a little later.",
                {"retry_after_s": wait},
            )
        hits.append(now)


def limited(bucket: str, setting: str):
    """A dependency that counts one use of `bucket`; the limit comes from the Settings field `setting`."""

    def dependency(
        context: AuthContext = Depends(get_auth_context), settings: Settings = Depends(get_settings)
    ) -> None:
        check(bucket, context.subject, getattr(settings, setting))

    return dependency
