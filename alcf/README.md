# ALCF Facility API Deployment

## Install application

Look at the main README to install your python environment with `make`. Make sure pip is installed:
```bash
source .venv/bin/activate
python -m ensurepip --upgrade
cd .venv/bin
ln -s pip3 pip
deactivate
cd ../../
source .venv/bin/activate
```

In the root folder of the project, activate your python environment and update required packages:
```bash
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
gunicorn -c gunicorn.config.py app.main:app
```

## Run application in a container

Build multi-architectures image (useful when building images from MacOS):
```bash
podman manifest create localhost/facility-api-prototype:<TAG>
podman build . --platform linux/arm64,linux/amd64 --manifest localhost/facility-api-prototype:<TAG>
```

Start the container in the background (served at http://localhost:8000):
```bash
podman run -d -p 8000:8000 facility-api-prototype:<TAG>
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

Login to ALCF GoHarbor
```bash
podman login goharbor.alcf.anl.gov
```

Build multi-architectures image:
```bash
podman manifest create goharbor.alcf.anl.gov/<USERNAME>/facility-api-prototype:<TAG>
podman build . --platform linux/arm64,linux/amd64 --manifest goharbor.alcf.anl.gov/<USERNAME>/facility-api-prototype:<TAG>
```

Push to GoHarbor
```bash
podman manifest push --all goharbor.alcf.anl.gov/<USERNAME>/facility-api-prototype:<TAG> docker://goharbor.alcf.anl.gov/<USERNAME>/facility-api-prototype:<TAG>
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
DATABASE_URL="sqlite+aiosqlite:///alcf/facilityapi.db"
API_URL_ROOT", "https://api.alcf.anl.gov"
IRI_API_ADAPTER="alcf.alcf_adapter.AlcfAdapter"
IRI_API_PARAMS='{ \
    "title": "ALCF implementation of the IRI Facility API", \
    "description": "A simple implementation of the IRI facility API for ALCF.\n\nFor more information, see: [https://iri.science/](https://iri.science/)\n\n<img src=\"https://iri.science/images/doe-icon-old.png\" height=50 />", \
    "docs_url": "/alcf/", \
    "contact": { \
        "name": "ALCF API contact", \
        "url": "https://www.alcf.anl.gov/" \
    } \
}'
```
