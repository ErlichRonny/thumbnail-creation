import json
import logging

from app.config import settings

# Standard attributes every LogRecord carries. Anything else on the record
# came from a caller's `logger.info(msg, extra={...})` and should be surfaced
# as its own structured field, not swallowed.
_STANDARD_LOG_RECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    # force=True replaces any handlers a prior basicConfig call (or uvicorn's
    # own logging setup) may have already installed on the root logger.
    logging.basicConfig(level=settings.log_level, handlers=[handler], force=True)
