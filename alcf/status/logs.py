import asyncio
import json
from uuid import uuid4
from functools import wraps

from alcf.config import LOG_BASE_PATH
from alcf.logging.async_logging import (
    BaseLog,
    AsyncBaseLogger,
    get_input_from_func,
    create_generic_logger_factory,
    run_and_log
)


# Decorator to log operations
# ===========================

def log_status_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Get fire-and-forget logger
        logger = await get_status_logger()
        
        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Initialize log
        status_log = BaseLog(
            id=str(uuid4()),
            api_route=f"status_{func.__name__}",
            input=input_data,
        )
        
        # Run operation and log after
        return await run_and_log(status_log, logger, func, *args, **kwargs)
        
    return wrapper


# Logger definition and execution
# ===============================

class AsyncStatusLogger(AsyncBaseLogger):
    """Class to write status logs to jsonl file."""

    def log_async(self, status_log: BaseLog) -> None:
        task = asyncio.create_task(write_status_log(status_log))
        self._background_tasks.add(task)
        task.add_done_callback(self._on_done)

async def write_status_log(status_log: BaseLog) -> None:
    _status_slog.info(json.dumps(status_log.model_dump(mode="json")))

_status_slog, get_status_logger = create_generic_logger_factory(
    "alcf.structured.status_log",
    LOG_BASE_PATH.joinpath("status_logs.jsonl"),
    AsyncStatusLogger
)