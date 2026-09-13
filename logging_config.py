import logging

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_configured = False


def _configure_once() -> None:
    global _configured
    if _configured:
        return
    logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Returns a configured logger. Call this once per module, at import time."""
    _configure_once()
    return logging.getLogger(name)