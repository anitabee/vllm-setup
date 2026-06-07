from __future__ import annotations

import logging

from rich.console import Console
from rich.logging import RichHandler


def setup(level: str = "WARNING") -> None:
    """Configure root logger to emit diagnostics via Rich on stderr."""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=Console(stderr=True), rich_tracebacks=True)],
    )
