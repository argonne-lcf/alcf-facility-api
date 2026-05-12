from uuid import uuid4
from functools import wraps
from app.types.user import User
from app.routers.status import models as status_models
from alcf.auth.utils import get_alcf_username_from_token
from alcf.logging.utils import get_input_from_func, run_and_log
from alcf.logging.schemas import (
    BaseLog,
    AccountLog,
    AuthenticatedAccountLog,
    AuthenticateComputeLog
)


def log_facility_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Initialize log
        facility_log = BaseLog(
            id=str(uuid4()),
            api_route=f"facility_{func.__name__}",
            input=input_data,
        )
        
        # Run operation and log after
        return await run_and_log(facility_log, func, *args, **kwargs)
        
    return wrapper


def log_status_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Initialize log
        status_log = BaseLog(
            id=str(uuid4()),
            api_route=f"status_{func.__name__}",
            input=input_data,
        )
        
        # Run operation and log after
        return await run_and_log(status_log, func, *args, **kwargs)
        
    return wrapper


def log_account_operation(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):

        # Gather input data
        input_data = get_input_from_func(func, *args, **kwargs)

        # Extract and remove user and resource objects from the input payload
        user: User = input_data.pop("user") if "user" in input_data else None

        # Initialize log
        if user:
            account_log = AuthenticatedAccountLog(
                id=str(uuid4()),
                api_route=f"account_{func.__name__}",
                input=input_data,
                user_id=user.id,
                user_name=user.name,
                ip=user.client_ip
            )
        else:
            account_log = AccountLog(
                id=str(uuid4()),
                api_route=f"account_{func.__name__}",
                input=input_data
            )

        # Run operation and log after
        return await run_and_log(account_log, func, *args, **kwargs)

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
        compute_log = AuthenticateComputeLog(
            id=str(uuid4()),
            api_route=f"compute_{func.__name__}",
            resource_id=resource.id,
            alcf_username=alcf_username,
            input=input_data,
            user_id=user.id,
            user_name=user.name,
            ip=user.client_ip
        )

        # Run operation and log after
        return await run_and_log(compute_log, func, *args, **kwargs)

    return wrapper