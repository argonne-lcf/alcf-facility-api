from app.routers.facility import models as facility_models
from app.routers.facility.facility_adapter import FacilityAdapter as FacilityFacilityAdapter
from fastapi import HTTPException
from starlette.status import HTTP_501_NOT_IMPLEMENTED
from alcf.database.database import get_db_facility_from_id, get_db_sites, get_db_site_from_id
from alcf.database import models as db_models

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


    # List sites
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

        # Gather sites from database
        sites = await get_db_sites(
            name=name,
            short_name=short_name,
            offset=offset,
            limit=limit,
        )

        # Format sites into IRI specification and return
        return [self.__format_site(site) for site in sites]

    # Get site
    async def get_site(
        self: "AlcfAdapter",
        site_id: str,
        modified_since: str | None = None,
    ) -> facility_models.Site | None:

        # Error for unsupported filters
        if modified_since:
            raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'modified_since' filter not supported yet.")

        # Gather site from database
        site = await get_db_site_from_id(
            id=site_id
        )

        # Format site into IRI specification and return
        return self.__format_site(site)


    # Format facility
    def __format_facility(self, db_facility: db_models.Facility) -> facility_models.Facility:
        """Format a database facility object into a pydantic facility object."""
        return facility_models.Facility(
            id=db_facility.id,
            name=db_facility.name,
            short_name=db_facility.short_name,
            description=db_facility.description,
            last_modified=db_facility.last_updated,
            organization_name=db_facility.organization_name,
            support_uri=db_facility.support_uri,
            site_ids=db_facility.site_ids,
        )

    # Format site
    def __format_site(self, db_site: db_models.Site) -> facility_models.Site:
        """Format a database site object into a pydantic site object."""
        return facility_models.Site(
            id=db_site.id,
            name=db_site.name,
            short_name=db_site.short_name,
            description=db_site.description,
            last_modified=db_site.last_updated,
            operating_organization=db_site.operating_organization,
            resource_ids=db_site.resource_ids,
            country_name=db_site.country_name,
            locality_name=db_site.locality_name,
            state_or_province_name=db_site.state_or_province_name,
            street_address=db_site.street_address,
            unlocode=db_site.unlocode,
            altitude=db_site.altitude,
            latitude=db_site.latitude,
            longitude=db_site.longitude,
        )