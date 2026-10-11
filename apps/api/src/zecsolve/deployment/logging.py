import json
import logging


class SafeFormatter(logging.Formatter):
    """Never format arbitrary messages/arguments, SQL parameters, URLs or tracebacks."""

    def format(self, record):
        return json.dumps(
            {
                "level": logging.getLevelName(record.levelno),
                "event": "runtime_error" if record.levelno >= logging.ERROR else "runtime_message",
            }
        )


LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {"safe": {"()": SafeFormatter}},
    "handlers": {"safe": {"class": "logging.StreamHandler", "formatter": "safe"}},
    "root": {"level": "INFO", "handlers": ["safe"]},
    "loggers": {
        "uvicorn": {"level": "INFO", "handlers": ["safe"], "propagate": False},
        "uvicorn.error": {"level": "INFO", "handlers": ["safe"], "propagate": False},
        "uvicorn.access": {"level": "CRITICAL", "handlers": [], "propagate": False},
    },
}
