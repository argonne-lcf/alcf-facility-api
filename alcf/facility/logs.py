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

def log_facility_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Get fire-and-forget logger
        logger = await get_facility_logger()
        
        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Initialize log
        facility_log = BaseLog(
            id=str(uuid4()),
            api_route=f"facility_{func.__name__}",
            input=input_data,
        )
        
        # Run operation and log after
        return await run_and_log(facility_log, logger, func, *args, **kwargs)
        
    return wrapper


# Logger definition and execution
# ===============================

class AsyncFacilityLogger(AsyncBaseLogger):
    """Class to write facility logs to jsonl file."""

    def log_async(self, facility_log: BaseLog) -> None:
        task = asyncio.create_task(write_facility_log(facility_log))
        self._background_tasks.add(task)
        task.add_done_callback(self._on_done)

async def write_facility_log(facility_log: BaseLog) -> None:
    _facility_slog.info(json.dumps(facility_log.model_dump(mode="json")))

_facility_slog, get_facility_logger = create_generic_logger_factory(
    "alcf.structured.facility_log",
    LOG_BASE_PATH.joinpath("facility_logs.jsonl"),
    AsyncFacilityLogger
)