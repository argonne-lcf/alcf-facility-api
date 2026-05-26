from functools import wraps
from app.types.user import User
from app.routers.status import models as status_models
from app.routers.account import models as account_models
from alcf.auth.utils import get_alcf_username_from_token
from alcf.logging.utils import get_input_from_func, run_and_log
from alcf.logging.schemas import (
    FacilityLog,
    StatusLog,
    AuthComputeLog,
    AccountLog,
    AuthAccountLog,
    AuthFilesystemLog,
    AuthTaskLog
)


def log_facility_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Initialize log
        log = FacilityLog(
            api_function=func.__name__,
            input=input_data,
        )
        
        # Run operation and log after
        return await run_and_log(log, func, *args, **kwargs)
        
    return wrapper


def log_status_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Initialize log
        log = StatusLog(
            api_function=func.__name__,
            input=input_data,
        )
        
        # Run operation and log after
        return await run_and_log(log, func, *args, **kwargs)
        
    return wrapper


def log_account_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Streamline input if possible
        if "project" in input_data:
            if isinstance(input_data["project"], account_models.Project):
                input_data["project_id"] = input_data["project"].id
                del input_data["project"]

        # Extract and remove user and resource objects from the input payload
        user: User = input_data.pop("user") if "user" in input_data else None

        # Initialize log
        if user:
            log = AuthAccountLog(
                api_function=func.__name__,
                input=input_data,
                user_id=user.id,
                user_name=user.name,
                ip=user.client_ip
            )
        else:
            log = AccountLog(
                api_function=func.__name__,
                input=input_data
            )

        # Run operation and log after
        return await run_and_log(log, func, *args, **kwargs)

    return wrapper


def log_compute_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Extract and remove user and resource objects from the input payload
        user: User = input_data.pop("user")
        resource: status_models.Resource = input_data.pop("resource")

        # Recover the ALCF username from the user's API key
        alcf_username, _ = get_alcf_username_from_token(user.api_key)

        # Initialize log
        log = AuthComputeLog(
            api_function=func.__name__,
            resource_id=resource.id,
            alcf_username=alcf_username,
            input=input_data,
            user_id=user.id,
            user_name=user.name,
            ip=user.client_ip
        )

        # Run operation and log after
        return await run_and_log(log, func, *args, **kwargs)

    return wrapper


def log_filesystem_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Extract and remove user and resource objects from the input payload
        user: User = input_data.pop("user")
        resource: status_models.Resource = input_data.pop("resource")

        # Initialize log
        log = AuthFilesystemLog(
            api_function=func.__name__,
            resource_id=resource.id,
            input=input_data,
            user_id=user.id,
            user_name=user.name,
            ip=user.client_ip
        )

        # Run operation and log after
        return await run_and_log(log, func, *args, **kwargs)

    return wrapper


def log_task_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Extract and remove user and resource objects from the input payload
        user: User = input_data.pop("user")

        # Initialize log
        log = AuthTaskLog(
            api_function=func.__name__,
            input=input_data,
            user_id=user.id,
            user_name=user.name,
            ip=user.client_ip
        )

        # Run operation and log after
        return await run_and_log(log, func, *args, **kwargs)

    return wrapper