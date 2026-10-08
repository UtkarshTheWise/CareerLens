"""Logging for the service: one JSON object per line on stdout (Render and most log tools read that).

`LOG_FORMAT=text` gives a readable line for local work. Extra fields passed with `extra={...}` become
JSON keys. The app never logs resume text, tokens, headers or request bodies; this module adds no field
that could carry them.
"""

import json
import logging
import sys
from datetime import UTC, datetime

_STANDARD = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime", "taskName"}
_MARK = "_careerlens_handler"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        data.update(
            {k: v for k, v in record.__dict__.items() if k not in _STANDARD and not k.startswith("_")}
        )
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extras = " ".join(
            f"{k}={v}" for k, v in record.__dict__.items() if k not in _STANDARD and not k.startswith("_")
        )
        line = f"{record.levelname:<7} {record.name}: {record.getMessage()} {extras}".rstrip()
        return line + ("\n" + self.formatException(record.exc_info) if record.exc_info else "")


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """Idempotent: replaces only the handler this function installed earlier."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, _MARK, False):
            root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(TextFormatter() if fmt == "text" else JsonFormatter())
    setattr(handler, _MARK, True)
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    logging.getLogger("uvicorn.access").disabled = True  # RequestLogMiddleware logs every request once
    # Libraries that would log what they are handed: httpx puts full URLs in INFO lines, and pdfminer's
    # DEBUG output contains the text of every PDF it reads, i.e. the student's resume.
    for noisy in ("httpx", "httpcore", "pdfminer", "pdfplumber", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
