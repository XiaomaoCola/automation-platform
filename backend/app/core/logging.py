from __future__ import annotations

import logging
import sys


def setup_logging() -> None:
    """
    Keep it simple:
    - logs to stdout
    - include level/name
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    # avoid duplicate handlers when reload/import happens
    if not root.handlers:
        root.addHandler(handler)
