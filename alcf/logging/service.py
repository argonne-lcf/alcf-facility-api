import asyncio
import json
import logging
from pydantic import BaseModel
from app.apilogger import get_stream_logger


class JsonFormatter(logging.Formatter):
    def format(self, record):
        message = record.getMessage()
        log_data = json.loads(message)
        log_data["level"] = record.levelname
        return json.dumps(log_data)


logger = get_stream_logger(__name__)
for handler in logger.handlers:
    handler.setFormatter(JsonFormatter())


async def write_logs(log_obj: BaseModel) -> None:
    logger.info(log_obj.model_dump_json())


class Service:
    """Service to handle logs in a fire-and-forget manner."""

    def __init__(self):
        self._background_tasks: set[asyncio.Task] = set()

    def _on_done(self, task: asyncio.Task) -> None:
        self._background_tasks.discard(task)

        try:
            task.result()
        except Exception:
            logger.exception("background logging task failed")

    def handle_log(self, log_obj: BaseModel):
        task = asyncio.create_task(write_logs(log_obj))
        self._background_tasks.add(task)
        task.add_done_callback(self._on_done)


# Create a reusable instance of the log service
log_service = Service()

