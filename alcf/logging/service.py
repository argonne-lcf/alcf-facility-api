import asyncio
import json
import logging
import sys
from pythonjsonlogger.json import JsonFormatter
from pydantic import BaseModel


class StructuredJsonFormatter(JsonFormatter):
    def format(self, record):
        message = record.getMessage()
        log_data = json.loads(message)
        log_data["level"] = record.levelname
        return json.dumps(log_data)


logger = logging.getLogger("alcf.structured_logs")
logger.setLevel(logging.INFO)
logger.propagate = False

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(StructuredJsonFormatter())
stdout_handler.setLevel(logging.INFO)
logger.addHandler(stdout_handler)


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

