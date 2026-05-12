import asyncio
import json
from uuid import uuid4
from functools import wraps
from pydantic import Field
from typing import Optional, Dict, Any

from app.types.user import User

from alcf.config import LOG_BASE_PATH
from alcf.logging.async_logging import (
    AuthenticatedBaseLog,
    AsyncBaseLogger,
    BaseLog,
    get_input_from_func,
    create_generic_logger_factory,
    run_and_log
)


class AccountLog(BaseLog):
    response: Optional[Dict[Any, Any]] = Field(default=None)


class AuthenticatedAccountLog(AuthenticatedBaseLog):
    response: Optional[Dict[Any, Any]] = Field(default=None)
    

# Decorator to log operations
# ===========================

def log_account_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Get fire-and-forget logger
        logger = await get_account_logger()

        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Extract and remove user and resource objects from the input payload
        user: User = input_data.pop("user") if "user" in input_data else None

        # Initialize log
        if user:
            account_log = AuthenticatedAccountLog(
                id=str(uuid4()),
                api_route=f"status_{func.__name__}",
                input=input_data,
                user_id=user.id,
                user_name=user.name
            )
        else:
            account_log = AccountLog(
                id=str(uuid4()),
                api_route=f"status_{func.__name__}",
                input=input_data
            )

        # Run operation and log after
        return await run_and_log(account_log, logger, func, *args, **kwargs)

    return wrapper


# Logger definition and execution
# ===============================

class AsyncAccountLogger(AsyncBaseLogger):
    """Class to write account logs to jsonl file."""

    def log_async(self, account_log: AccountLog) -> None:
        task = asyncio.create_task(write_account_log(account_log))
        self._background_tasks.add(task)
        task.add_done_callback(self._on_done)

async def write_account_log(account_log: AccountLog) -> None:
    _account_slog.info(json.dumps(account_log.model_dump(mode="json")))

_account_slog, get_account_logger = create_generic_logger_factory(
    "alcf.structured.account_log",
    LOG_BASE_PATH.joinpath("account_logs.jsonl"),
    AsyncAccountLogger
)