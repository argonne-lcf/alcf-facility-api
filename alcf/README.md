# ALCF Facility API Deployment

## Install application

Look at the main README to install your python environment with `make`. In the root folder of the project, activate your python environment and update required packages:
```bash
source .venv/bin/activate
uv pip install -r alcf/requirements.txt
```

Test FastAPI service in development mode (served at http://localhost:8000):

```bash
fastapi dev app/main.py
```

Test FastAPI with Uvicorn:
```bash
uvicorn app.main:app
```

Test FastAPI with Gunicorn with Uvicorn workers (logs will be stored in the `logs/` folder):
```bash
gunicorn -c gunicorn.config.production.py app.main:app
```

## Run application in a container

Define variable names:
```bash
IMAGE_NAME="your_image_name"
IMAGE_TAG="your_image_tag"
```

Build image:
```bash
podman build -f Dockerfile.production -t $IMAGE_NAME:$IMAGE_TAG .
```

Start the container in the background (served at http://localhost:8000):
```bash
podman run --rm -d -p 8000:8000 --env-file .env $IMAGE_NAME:$IMAGE_TAG
```

Check running container ID:
```bash
podman container list
```

Stop container:
```bash
podman container stop <CONTAINER-ID>
```

## Build image and push it to GoHarbor

Define variable names:
```bash
IMAGE_NAME="your_image_name"
IMAGE_TAG="your_image_tag"
GOHARBOR_PROJECT="your_goharbor_project"
```

Authenticate to your ALCF GoHarbor project (need to be on the VPN, need to use a robot-account):
```bash
podman login goharbor.alcf.anl.gov/$GOHARBOR_PROJECT
```

If you have credential issues, you may need to logout and log back in
```bash
podman logout goharbor.alcf.anl.gov
podman login goharbor.alcf.anl.gov/$GOHARBOR_PROJECT
```

Build multi-architectures image (useful when building images from MacOS):
```bash
podman manifest create goharbor.alcf.anl.gov/$GOHARBOR_PROJECT/$IMAGE_NAME:$IMAGE_TAG
podman build -f Dockerfile.production . --platform linux/arm64,linux/amd64 --manifest goharbor.alcf.anl.gov/$GOHARBOR_PROJECT/$IMAGE_NAME:$IMAGE_TAG
```

Push to GoHarbor
```bash
podman manifest push --all goharbor.alcf.anl.gov/$GOHARBOR_PROJECT/$IMAGE_NAME:$IMAGE_TAG docker://goharbor.alcf.anl.gov/$GOHARBOR_PROJECT/$IMAGE_NAME:$IMAGE_TAG
```

## Run test suite

Launch the following command to trigger the tests (using pytest and coverage):
```bash
pytest --cov=app app/tests/
```

## Generate specs from Pydantic models

```python
import json
from app.utils_classes import Facility
facility_model_schema = Facility.model_json_schema()
print(json.dumps(facility_model_schema, indent=2))
```

## Environment File

Create an environment variable file (`.env`) with the following:
```bash
API_URL_ROOT="http://localhost:8000"
API_URL="api/current"

DATABASE_URL="sqlite+aiosqlite:///alcf/facilityapi.db"

IRI_API_ADAPTER_status="alcf.status.alcf_adapter.AlcfAdapter"
IRI_API_ADAPTER_compute="alcf.compute.alcf_adapter.AlcfAdapter"
IRI_API_PARAMS='{
    "title": "ALCF implementation of the IRI Facility API",
    "description": "IRI facility API for ALCF.\n\nFor more information, see: [https://iri.science/](https://iri.science/)\n\n<img src=\"https://iri.science/images/doe-icon-old.png\" height=50 />",
    "docs_url": "/",
    "contact": {
        "name": "ALCF API contact",
        "url": "https://www.alcf.anl.gov/"
    }
}'

IRI_SHOW_MISSING_ROUTES=False

GRAPHQL_URL="https://your-api-url"
```
