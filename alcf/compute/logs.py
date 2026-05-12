import asyncio
import json
from uuid import uuid4
from functools import wraps
from pydantic import Field
from typing import Optional, Dict, Any

from app.routers.status import models as status_models
from app.types.user import User

from alcf.config import LOG_BASE_PATH
from alcf.auth.utils import get_alcf_username_from_token
from alcf.logging.async_logging import (
    AuthenticatedBaseLog,
    AsyncBaseLogger,
    get_input_from_func,
    create_generic_logger_factory,
    run_and_log
)


class ComputeLog(AuthenticatedBaseLog):
    resource_id: str
    alcf_username: str
    response: Optional[Dict[Any, Any]] = Field(default=None)
    

# Decorator to log operations
# ===========================

def log_compute_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Get fire-and-forget logger
        logger = await get_compute_logger()

        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

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
            input=input_data,
            user_id=user.id,
            user_name=user.name
        )

        # Run operation and log after
        return await run_and_log(compute_log, logger, func, *args, **kwargs)

    return wrapper


# Logger definition and execution
# ===============================

class AsyncComputeLogger(AsyncBaseLogger):
    """Class to write compute logs to jsonl file."""

    def log_async(self, compute_log: ComputeLog) -> None:
        task = asyncio.create_task(write_compute_log(compute_log))
        self._background_tasks.add(task)
        task.add_done_callback(self._on_done)

async def write_compute_log(compute_log: ComputeLog) -> None:
    _compute_slog.info(json.dumps(compute_log.model_dump(mode="json")))

_compute_slog, get_compute_logger = create_generic_logger_factory(
    "alcf.structured.compute_log",
    LOG_BASE_PATH.joinpath("compute_logs.jsonl"),
    AsyncComputeLogger
)