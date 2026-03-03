#!/bin/bash

# Populate database
python alcf/database/ingestion/ingest_static_data.py

# Update (if needed) the status of resources
python alcf/database/ingestion/ingest_activity_data.py

# Run application
gunicorn app.main:APP -c gunicorn.config.production.py -k uvicorn.workers.UvicornWorker