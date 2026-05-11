import asyncio
import json
import inspect
from uuid import uuid4
from functools import cache, wraps
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from starlette.status import HTTP_200_OK
from fastapi import HTTPException

from alcf.config import LOG_BASE_PATH
from alcf.logging.async_logging import setup_structured_logger, AsyncBaseLogger


# Data format for the log
class StatusLog(BaseModel):
    id: str
    api_route: str
    status_code: Optional[int] = Field(default=None)
    input: Dict[Any, Any]
    error: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    

# Decorator to be added to every status function
def track_status_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Get fire-and-forget logger
        logger = await get_status_logger()
        
        # Gather input data
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        input_data = dict(bound_args.arguments)
        input_data.pop('self', None)

        # Initialize log
        status_log = StatusLog(
            id=str(uuid4()),
            api_route=f"status_{func.__name__}",
            input=input_data,
        )
        
        # Run operation and log after
        try:
            result = await func(*args, **kwargs)
            status_log.status_code = HTTP_200_OK
            logger.log_async(status_log)
            return result
        
        # Propagate error in the log (if any)
        except HTTPException as e:
            status_log.status_code = e.status_code
            status_log.error = str(e.detail)
            logger.log_async(status_log)
            raise

    return wrapper


# Logger definition and execution
# ===============================

_status_lock = asyncio.Lock()

_status_slog = setup_structured_logger(
    "alcf.structured.status_log",
    LOG_BASE_PATH.joinpath("status_logs.jsonl")
)

class AsyncStatusLogger(AsyncBaseLogger):
    """Class to write status logs to jsonl file."""

    def log_async(self, status_log: StatusLog) -> None:
        task = asyncio.create_task(write_status_log(status_log))
        self._background_tasks.add(task)
        task.add_done_callback(self._on_done)

async def write_status_log(status_log: StatusLog) -> None:
    _status_slog.info(json.dumps(status_log.model_dump(mode="json")))

@cache
def _create_status_logger() -> AsyncStatusLogger:
    return AsyncStatusLogger()
async def get_status_logger() -> AsyncStatusLogger:
    async with _status_lock:
        return _create_status_logger()