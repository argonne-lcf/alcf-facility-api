# <img src="https://iri.science/images/doe-icon-old.png" height=30 /> IRI API reference implementation in Python 3
Python reference implementation of the IRI facility API, standardizing endpoints, parameters, and return values across DOE computational facilities.

See it live (NERSC instance): https://api.iri.nersc.gov/nersc/api/current/

## Prerequisites

- [install python3](https://www.python.org/downloads/) (version 3.8 or higher)
- [install uv](https://docs.astral.sh/uv/getting-started/installation/)
- make

## Start the dev server

`make`

This will set up a virtual environment, install the dependencies and run the fastApi dev server. Code changes will automatically reload
in the server. To exit, press ctrl+C. This will stop the server and deactivate the virtual environment.

On Windows, see the [Makefile](Makefile) and run the commands manually.

## Visit the dev server

[http://127.0.0.1:8000/api/current/](http://127.0.0.1:8000/api/current/)

## Customizing the API for your facility

The reference implementation is meant to be customized for your facility's IRI implementation. Running the IRI api unmodified will show only fake, test data. The paragraphs below describe how to customize the business logic and appearance of the API for your facility.

### Customizing the business logic for your facility
The IRI API handles the "boilerplate" of setting up the rest API. It delegates to the per-facility business logic via interface definitions. These interfaces are implemented as abstract classes, one per api group (status, account, etc.). Each router directory defines a FacilityAdapter class (eg. [the status adapter](app/routers/status/facility_adapter.py)) that is expected to be implemented by the facility who is exposing an IRI API instance. 

The specific implementations can be specified via the `IRI_API_ADAPTER_*` environment variables. For example the adapter for the `status` api would be given by setting `IRI_API_ADAPTER_status` to the full python module and class implementing `app.routers.status.facility_adapter.FacilityAdapter`. (eg. `IRI_API_ADAPTER_status=myfacility.MyFacilityStatusAdapter`)

As a default implementation, this project supplies the [demo adapter](app/demo_adapter.py) which implements every facility adapter with fake data. 

### Customizing the API meta-data
You can optionally override the [FastAPI metadata](https://fastapi.tiangolo.com/tutorial/metadata/), such as `name`, `description`, `terms_of_service`, etc. by providing a valid json object in the `IRI_API_PARAMS` environment variable.

If using docker (see next section), your dockerfile could extend this reference implementation via a `FROM` line and add your custom facility adapter code and init parameters in `ENV` lines.

### Environment variables

- `API_URL_ROOT`: the base url when constructing links returned by the api (eg.: https://iri.myfacility.com)
- `API_PREFIX`: the path prefix where the api is hosted. Defaults to `/`. (eg.: `/api`)
- `API_URL`: the path to the api itself. Defaults to `api/current`.

Links to data, created by this api, will concatenate these values producing links, eg: `https://iri.myfacility.com/my_api_prefix/my_api_url/projects/123`

- `IRI_API_PARAMS`: as described above, this is a way to customize the API meta-data
- `IRI_API_ADAPTER_*`: these values specify the business logic for the per-api-group implementation of a facility_adapter. For example: `IRI_API_ADAPTER_status=myfacility.MyFacilityStatusAdapter` would load the implementation of the `app.routers.status.facility_adapter.FacilityAdapter` abstract class to handle the `status` business logic for your facility.
- `IRI_SHOW_MISSING_ROUTES`: hide api groups that don't have an `IRI_API_ADAPTER_*` environment variable defined, if set to `true`. This way if your facility only wishes to expose some api groups but not others, they can be hidden. (Defaults to `false`.)

## Docker support

You can build and run the included dockerfile, for example:
`docker build -t iri . && docker run -p 8000:8000 iri`

Docker is also recommended for running your facility implementation. For example, supposing you have built an image for the reference implementation and stored it in your docker registry, you could use the following Dockerfile for your IRI api:

```Dockerfile
FROM registry.myfacility.gov/isg/iri/iri:main

COPY ./your_businesslogic /app/your_businesslogic/

RUN pip install -U pip
RUN pip install -U wheel
RUN pip install -U setuptools
RUN pip install additional_libraries

ENV IRI_API_ADAPTER_status="myfacility.status_adapter.StatusAdapter"
ENV IRI_API_ADAPTER_account="myfacility.account_adapter.AccountAdapter"
ENV IRI_API_ADAPTER_compute="myfacility.compute_adapter.ComputeAdapter"
ENV API_PREFIX="/myfacility/"
ENV IRI_API_PARAMS='{ \
    "title": "Facility XYZ implementation of the IRI api", \
    "terms_of_service": "https://myfacility.gov/aup", \
    "docs_url": "/", \
    "contact": { \
        "name": "My Facility Contact", \
        "url": "https://myfacility.gov/about/contact-us/" \
    } \
}'
```

## Next steps

- Learn more about [fastapi](https://fastapi.tiangolo.com/), including how to run it [in production](https://fastapi.tiangolo.com/advanced/behind-a-proxy/)
- Instead of the simulated state, keep real data in a [database](/Users/gtorok/dev/iri-api-python/README.md)
- Add monitoring by [integrating with OpenTelemetry](https://opentelemetry.io/docs/zero-code/python/)
- Add additional routers for other API-s
- Add authenticated API-s via an [OAuth2 integration](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)

