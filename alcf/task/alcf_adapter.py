from app.routers.task.facility_adapter import FacilityAdapter as TaskFacilityAdapter
from app.routers.status import models as status_models
from app.routers.account import models as account_models
from app.routers.task import models as task_models
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter

class AlcfAdapter(TaskFacilityAdapter, AlcfAuthenticatedAdapter):
    """Filesystem facility adapter definition for the IRI Facility API."""

    async def get_task(
        self : "AlcfAdapter",
        user: account_models.User,
        task_id: str,
        ) -> task_models.Task|None:
        pass


    async def get_tasks(
        self : "AlcfAdapter",
        user: account_models.User,
        ) -> list[task_models.Task]:
        pass


    async def put_task(
        self: "AlcfAdapter",
        user: account_models.User,
        resource: status_models.Resource|None,
        command: task_models.TaskCommand
    ) -> str:
        pass