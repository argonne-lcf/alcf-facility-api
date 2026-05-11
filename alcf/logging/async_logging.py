import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from logging import getLogger
from pydantic import BaseModel


logger = getLogger(__name__)


def setup_structured_logger(logger_name: str, log_file: Path) -> logging.Logger:
    slog = logging.getLogger(logger_name)
    slog.setLevel(logging.INFO)
    
    if not slog.handlers:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        
        slog.addHandler(handler)
        slog.propagate = False
    
    return slog


class AsyncBaseLogger(ABC):
    """Base class to write logs to jsonl file."""

    def __init__(self):
        self._background_tasks: set[asyncio.Task[None]] = set()

    def _on_done(self, task: asyncio.Task[None]) -> None:
        self._background_tasks.discard(task)
        if task.cancelled():
            return
        if exc := task.exception():
            logger.error("Background log write failed", exc_info=exc)

    @abstractmethod
    def log_async(self, log: BaseModel) -> None:
        """Fire-and-forget logging"""
        pass
