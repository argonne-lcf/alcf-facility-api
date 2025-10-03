import os
import importlib
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .facility_adapter import FacilityAdapter
from . import config
from .database import DATABASE_ENABLED, DATABASE_URL

# include other sub-components as needed
from app.routers.status import status
from app.routers.account import account
from app.routers.compute import compute


api_app = FastAPI(**config.API_CONFIG)
api_app.include_router(status.router)
api_app.include_router(account.router)
api_app.include_router(compute.router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the facility-specific adapter
    adapter_name = os.environ.get("IRI_API_ADAPTER", "app.demo_adapter.DemoAdapter")
    logging.getLogger().info(f"Using adapter: {adapter_name}")
    if DATABASE_ENABLED:
        logging.getLogger().info(f"\tDatabase enabled ({DATABASE_URL}) - assuming existing database with tables.")
    parts = adapter_name.rsplit(".", 1)
    module = importlib.import_module(parts[0])    
    AdapterClass = getattr(module, parts[1])
    if not issubclass(AdapterClass, FacilityAdapter):
        raise Exception(f"{adapter_name} should implement FacilityAdapter")
    logging.getLogger().info("\tSuccessfully loaded adapter.")
    api_app.state.adapter = AdapterClass()

    yield


app = FastAPI(lifespan=lifespan)


# for non-backward compatible versions, we can mount specific versions, eg. /api/v1
# but, /api/current is always the latest
app.mount(config.API_CONFIG["docs_url"] + config.API_URL, api_app)

logging.getLogger().info("API path: %s" % config.API_CONFIG["docs_url"] + config.API_URL)
