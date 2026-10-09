import logging
import sys
from pathlib import Path

def setup_logging(log_dir: Path | str = ".", level: int = logging.INFO) -> None:
    """
    Configures the baseline logging for the application.
    
    Convention:
    - Every module should instantiate its own logger: `logger = logging.getLogger(__name__)`
    - Use `logger.debug()` for tracing layout/UI events and SQL queries.
    - Use `logger.info()` for major app lifecycle events (app start, DB migration, file import).
    - Use `logger.warning()` for handled anomalies (e.g. missing thumbnail).
    - Use `logger.exception()` for caught system errors that we are logging.
    """
    log_path = Path(log_dir) / "family_tree.log"
    
    # Standard format: Time | Level | Module:Line | Message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler (keeps a persistent record)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Console handler (useful during development)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Prevent adding handlers multiple times if called twice
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(stream_handler)
