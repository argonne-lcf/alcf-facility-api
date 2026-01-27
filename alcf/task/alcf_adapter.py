from fastapi import HTTPException
from starlette.status import HTTP_501_NOT_IMPLEMENTED, HTTP_404_NOT_FOUND
from app.routers.task.facility_adapter import FacilityAdapter as TaskFacilityAdapter
from app.routers.status import models as status_models
from app.routers.account import models as account_models
from app.routers.task import models as task_models
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter

# Instantiate the Filesystem adaptor
from alcf.filesystem.alcf_adapter import AlcfAdapter as FilesystemAdaptor
filesystem_adaptor = FilesystemAdaptor()
filesystem_commands = {
    "ls": filesystem_adaptor.ls
}

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


    # Put task
    async def put_task(
        self: "AlcfAdapter",
        user: account_models.User,
        resource: status_models.Resource|None,
        command: task_models.TaskCommand
    ) -> str:
        
        # Create input dictionary
        kwargs = {"user": user, "resource": resource} | command.args

        # Filesystem operations
        if command.router == "filesystem":

            # Supported commands
            if command.command in filesystem_commands:
                return await filesystem_commands[command.command](**kwargs)
            
            # Unsupported commands
            else:
                raise HTTPException(status_code=HTTP_501_NOT_IMPLEMENTED, detail="'recursive' option not implemented yet.")

        # Other operations not implemented yet
        else: 
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Router {command.router} not found.")
        