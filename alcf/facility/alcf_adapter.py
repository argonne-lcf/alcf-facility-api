from app.routers.facility import models as facility_models
from app.routers.facility.facility_adapter import FacilityAdapter as FacilityFacilityAdapter
from alcf.database.database import get_db_facilities, get_db_sites
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

        # Gather facility from database
        facilities = await get_db_facilities(
            ids=[self.FACILITY_ID],
            modified_since=modified_since,
        )

        # Format facility into IRI specification and return
        if facilities:
            return self.__format_facility(facilities[0])
        else:
            return None


    # List sites
    async def list_sites(
        self: "AlcfAdapter",
        modified_since: str | None = None, 
        name: str | None = None, 
        offset: int | None = None, 
        limit: int | None = None, 
        short_name: str | None = None
        ) -> list[facility_models.Site]:

        # Gather sites from database
        sites = await get_db_sites(
            name=name,
            short_name=short_name,
            offset=offset,
            limit=limit,
            modified_since=modified_since,
        )

        # Format sites into IRI specification and return
        return [self.__format_site(site) for site in sites]

    # Get site
    async def get_site(
        self: "AlcfAdapter",
        site_id: str,
        modified_since: str | None = None,
    ) -> facility_models.Site | None:

        # Gather site from database, filtered by modified_since
        sites = await get_db_sites(
            ids=[site_id],
            modified_since=modified_since,
        )

        # Format site into IRI specification and return
        if sites:
            return self.__format_site(sites[0])
        else:
            return None


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