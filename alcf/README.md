# ALCF Facility API Deployment

## Install application

Look at the main README to install your python environment with `make`. In the root folder of the project, activate your python environment and update required packages:
```bash
source .venv/bin/activate
uv pip install -r alcf/requirements.txt
```

Create and load database
```bash
python alcf/database/ingestion/ingest_static_data.py
```

If you have issues with `no module named 'alcf'`, you might have to type:
```bash
pip install -e .
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
GOHARBOR_PROJECT="alcf-facility-api"
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

To deploy on Kubernetes, please see [https://gitlab-ci.alcf.anl.gov/anl/artemis/showcase/facility-api](https://gitlab-ci.alcf.anl.gov/anl/artemis/showcase/facility-api)

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
IRI_API_ADAPTER_filesystem=alcf.filesystem.alcf_adapter.AlcfAdapter
IRI_API_ADAPTER_task=alcf.task.alcf_adapter.AlcfAdapter
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

# Keycloak integration
KEYCLOAK_CLIENT_ID="PBS-EDTB"
KEYCLOAK_CLIENT_SECRET="your-keycloak-secret"
KEYCLOAK_REALM_NAME="PBS-EDTB"
KEYCLOAK_SERVER_URL="https://keycloak-internal.alcf.anl.gov/realms/PBS-EDTB"
KEYCLOAK_AUTHORIZATION_ENDPOINT="https://keycloak-internal.alcf.anl.gov/realms/PBS-EDTB/protocol/openid-connect/auth"
KEYCLOAK_REDIRECT_URI="http://localhost:8000/auth/callback"


# Compute functions -> function_name: function_UUID
GLOBUS_COMPUTE_FUNCTIONS='
{
    "chmod": "8f9a8eb8-495c-4122-a7cf-44c616d98d1b",
    "chown": "6e8635cc-1f90-4051-bbbe-f44a0135ab50",
    "ls": "1b1dc9be-b6e1-48f0-96e5-ad42cbd3b7f0",
    "head": "ee15b751-fb5c-43ef-be27-856c5073fac2",
    "view": "7494c19d-3967-43c9-9240-f99dbcf77661"
}
'
# Compute endpoints -> resource_name: endpoint_UUID
GLOBUS_COMPUTE_ENDPOINTS='
{  
    "edith": "your-globus-compute-endpoint"
}
'
```
