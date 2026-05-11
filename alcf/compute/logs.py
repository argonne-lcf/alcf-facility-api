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

from app.routers.status import models as status_models
from app.types.user import User

from alcf.config import LOG_BASE_PATH
from alcf.logging.async_logging import setup_structured_logger, AsyncBaseLogger
from alcf.auth.utils import get_alcf_username_from_token


# Data format for the log
class ComputeLog(BaseModel):
    id: str
    api_route: str
    resource_id: str
    alcf_username: str
    status_code: Optional[int] = Field(default=None)
    input: Dict[Any, Any]
    response: Optional[Dict[Any, Any]] = Field(default=None)
    error: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    

# Decorator to be added to every compute function
def track_compute_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Get fire-and-forget logger
        logger = await get_compute_logger()

        # Gather input data
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        input_data = dict(bound_args.arguments)
        input_data.pop('self', None)

        # Extract and remove user and resource objects from the input payload
        user: User = input_data.pop("user")
        resource: status_models.Resource = input_data.pop("resource")

        # Recover the ALCF username from the user's API key
        alcf_username, _ = get_alcf_username_from_token(user.api_key)

        # Initialize log
        compute_log = ComputeLog(
            id=str(uuid4()),
            api_route=f"status_{func.__name__}",
            resource_id=resource.id,
            alcf_username=alcf_username,
            input=input_data
        )

        # Run operation and log after
        try:
            result = await func(*args, **kwargs)
            compute_log.status_code = HTTP_200_OK
            compute_log.response = result
            logger.log_async(compute_log)
            return result
        
        # Propagate error in the log (if any)
        except HTTPException as e:
            compute_log.status_code = e.status_code
            compute_log.error = str(e.detail)
            logger.log_async(compute_log)
            raise

    return wrapper


# Logger definition and execution
# ===============================

_compute_lock = asyncio.Lock()

_compute_slog = setup_structured_logger(
    "alcf.structured.compute_log",
    LOG_BASE_PATH.joinpath("compute_logs.jsonl")
)

class AsyncComputeLogger(AsyncBaseLogger):
    """Class to write compute logs to jsonl file."""

    def log_async(self, compute_log: ComputeLog) -> None:
        task = asyncio.create_task(write_compute_log(compute_log))
        self._background_tasks.add(task)
        task.add_done_callback(self._on_done)

async def write_compute_log(compute_log: ComputeLog) -> None:
    _compute_slog.info(json.dumps(compute_log.model_dump(mode="json")))

@cache
def _create_compute_logger() -> AsyncComputeLogger:
    return AsyncComputeLogger()
async def get_compute_logger() -> AsyncComputeLogger:
    async with _compute_lock:
        return _create_compute_logger()