import logging
import sys
from typing import Optional


def setup_logger(level: str = "INFO", format_string: Optional[str] = None) -> None:
    """
    Setup logging for the entire pipeline with consistent settings.
    Call this once at the start of your application.

    Args:
        level (str): Logging level for all pipeline components
        format_string (str, optional): Custom format string for log messages
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger for the entire application
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # Override any existing configuration
    )
