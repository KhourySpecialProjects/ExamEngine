"""Application logging: the `examengine` logger tree writes to stdout."""

import logging
import sys


APP_LOGGER = "examengine"
_HANDLER_NAME = "examengine-stdout"
_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Send `examengine.*` records at `level` and above to stdout, timestamped.

    Only the application's own logger is configured, so uvicorn's and other
    libraries' loggers keep their handlers. Calling this again changes nothing.
    """
    logger = logging.getLogger(APP_LOGGER)
    logger.setLevel(level)
    if any(handler.get_name() == _HANDLER_NAME for handler in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(logging.Formatter(_FORMAT))
    logger.addHandler(handler)
