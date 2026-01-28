from fastapi import HTTPException
from typing import Tuple
from copy import deepcopy
from starlette.status import (
    HTTP_501_NOT_IMPLEMENTED, 
    HTTP_404_NOT_FOUND, 
    HTTP_403_FORBIDDEN, 
    HTTP_500_INTERNAL_SERVER_ERROR
)
from app.routers.task.facility_adapter import FacilityAdapter as TaskFacilityAdapter
from app.routers.status import models as status_models
from app.routers.account import models as account_models
from app.routers.task import models as task_models
from alcf.task.utils import filesystem_commands, filesystem_format_functions, filesystem_model_responses
from alcf.auth.alcf_adapter import AlcfAuthenticatedAdapter
from alcf.database.database import add_task_to_db, update_task_in_db, get_db_task_from_id, get_db_tasks_by_user
from alcf.globus.utils import get_task_status
import json
import logging
log = logging.getLogger(__name__)



class AlcfAdapter(TaskFacilityAdapter, AlcfAuthenticatedAdapter):
    """Task facility adapter definition for the IRI Facility API."""

    # Get task
    async def get_task(
        self : "AlcfAdapter",
        user: account_models.User,
        task_id: str,
        ) -> task_models.Task|None:

        # Retrieve task from database
        db_task = await get_db_task_from_id(task_id)
        
        # Verify the task was submitted by the user
        if db_task.user_id != user.id:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, 
                detail="Task does not belong to user."
            )

        # Convert the database task into an IRI Task model and update if needed
        iri_task = self._convert_db_task_to_iri_task(db_task)
        iri_task = await self._update_iri_task(user, iri_task)

        # Return IRI task
        return iri_task


    # Get tasks
    async def get_tasks(
        self : "AlcfAdapter",
        user: account_models.User,
        ) -> list[task_models.Task]:

        # Retrieve all tasks for the user from database
        db_tasks = await get_db_tasks_by_user(user.id)
        
        # Convert all database tasks into IRI Task models (and update if needed)
        tasks = []
        for db_task in db_tasks:
            try:
                iri_task = self._convert_db_task_to_iri_task(db_task)
                iri_task = await self._update_iri_task(user, iri_task)
                tasks.append(iri_task)
            except Exception as e:
                log.warning(f"Could not convert database model to IRI Task model: {e}")
                continue
        
        # Return the list of IRI Task models
        return tasks


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

            # If this is a supported command ...
            if command.command in filesystem_commands:

                # Execute the command and get the task ID
                task_id = await filesystem_commands[command.command](**kwargs)

                # Create task entry in database
                await add_task_to_db({
                    "id": task_id,
                    "user_id": user.id,
                    "status": task_models.TaskStatus.pending.value,
                    "command": json.dumps(command.model_dump()),
                    "result": None
                })
                
                # Return the task ID to the user
                return task_id
            
            # Unsupported commands
            else:
                raise HTTPException(
                    status_code=HTTP_501_NOT_IMPLEMENTED, 
                    detail=f"Command {command.command} option not implemented yet."
                )

        # Other operations not implemented yet
        else:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, 
                detail=f"Router {command.router} not found."
            )
        

    # Convert DB task to IRI task
    def _convert_db_task_to_iri_task(self, db_task) -> task_models.Task:
        """Convert a database Task model to an IRI Task model."""

        # Convert database data to IRI TaskCommand model
        try:
            command_dict = json.loads(db_task.command) if db_task.command else None
            command = task_models.TaskCommand(**command_dict) if command_dict else None
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not convert database command to IRI TaskCommand model: {e}"
            )
        
        # Convert database data to IRI Task model
        try:
            iri_task = task_models.Task(
                id=db_task.id,
                status=task_models.TaskStatus(db_task.status),
                result=db_task.result,
                command=command
            )
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not convert database model to IRI Task model: {e}"
            )
        
        # Format database result if completed successfully
        try:
            if iri_task.status == task_models.TaskStatus.completed.value:
                if iri_task.result:
                    if iri_task.command.command in filesystem_model_responses:
                        iri_task.result = filesystem_model_responses[iri_task.command.command](**json.loads(iri_task.result))
                    else:
                        iri_task.result = json.loads(iri_task.result)
        except Exception as e:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not format IRI Task result field: {e}"
            )
        
        # Return the IRI Task object
        return iri_task


    # Update IRI task
    async def _update_iri_task(self, user: account_models.User, iri_task: task_models.Task) -> task_models.Task:
            
        # If the task status should be checked and updated ...
        if iri_task.status in [task_models.TaskStatus.pending.value, task_models.TaskStatus.active.value]:

            # Query latest status for the task
            status, result = get_task_status(user, iri_task.id)

            # If the task status changed ...
            if status != iri_task.status:

                # Format result if a raw successful result got generated
                result_for_db = deepcopy(result)
                if result:
                    try:
                        if status == task_models.TaskStatus.completed.value:
                            result = filesystem_format_functions[iri_task.command.command](result)
                            if isinstance(result, Tuple):
                                result_for_db = json.dumps(result)
                            else:
                                result_for_db = json.dumps(result.model_dump())
                    except Exception as e:
                        raise HTTPException(
                            status_code=HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail=f"Could not format result: {e}"
                        )

                # Update IRI task data
                iri_task.status = status
                iri_task.result = result

                # Update status and result in database
                try:
                    await update_task_in_db({
                        "id": iri_task.id,
                        "status": status,
                        "result": result_for_db
                    })
                except Exception as e:
                    raise HTTPException(
                        status_code=HTTP_500_INTERNAL_SERVER_ERROR, 
                        detail=f"Could not update database: {e}"
                    )

        # Return IRI task (updated or original)
        return iri_task