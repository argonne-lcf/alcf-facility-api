import asyncio
import logging
import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from logging import getLogger
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from starlette.status import HTTP_200_OK
from fastapi import HTTPException


logger = getLogger(__name__)


class BaseLog(BaseModel):
    id: str
    api_route: str
    status_code: Optional[int] = Field(default=None)
    input: Dict[Any, Any]
    error: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    @classmethod
    def has_field(cls, field_name: str) -> bool:
        return field_name in cls.model_fields
    

class AuthenticatedBaseLog(BaseLog):
    user_id: str
    user_name: str


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


def get_input_from_func(func, *args, **kwargs) -> Dict:
    """Inspect the signature of a function and generate a dictionary with all inputs"""
    
    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()
    
    input_data = dict(bound_args.arguments)
    input_data.pop('self', None)
    
    return input_data


async def run_and_log(
    log: BaseLog,
    logger: AsyncBaseLogger, 
    func, *args, **kwargs
) -> Any:
    """Run function and log the outcome."""
    
    try:
        result = await func(*args, **kwargs)
        log.status_code = HTTP_200_OK
        if log.has_field("response"):
            log.response = result
        logger.log_async(log)
        return result
            
    except HTTPException as e:
        log.status_code = e.status_code
        log.error = str(e.detail)
        logger.log_async(log)
        raise
