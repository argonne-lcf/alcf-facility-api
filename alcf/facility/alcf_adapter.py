from app.routers.facility import models as facility_models
#from ..iri_router import AuthenticatedAdapter
from app.routers.facility.facility_adapter import FacilityAdapter as FacilityFacilityAdapter
from fastapi import HTTPException
from starlette.status import HTTP_501_NOT_IMPLEMENTED
from alcf.database.database import get_db_facility_from_id, get_db_sites, get_db_site_from_id

class AlcfAdapter(FacilityFacilityAdapter):
    """Facility adapter definition for the Facility component of the IRI Facility API."""

    # Facility ID (must be the same as in the database)
    FACILITY_ID = "8da81144-304b-4fd0-b2fe-eda33bb38720"

    # Get facility
    async def get_facility(
        self: "AlcfAdapter",
        modified_since: str | None = None
        ) -> facility_models.Facility | None:

        # Error for unsupported filters
        if modified_since:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'modified_since' filter not supported yet.")

        # Gather resources from database
        facility = await get_db_facility_from_id(
            id=self.FACILITY_ID
        )

        # Format facility into IRI specification and return
        return self.__format_facility(facility)


    async def list_sites(
        self: "AlcfAdapter",
        modified_since: str | None = None,
        name: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
        short_name: str | None = None
        ) -> list[facility_models.Site]:

        # Error for unsupported filters
        if modified_since:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'modified_since' filter not supported yet.")

    async def get_site(
        self: "AlcfAdapter",
        site_id: str,
        modified_since: str | None = None,
    ) -> facility_models.Site | None:

        # Error for unsupported filters
        if modified_since:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'modified_since' filter not supported yet.")
