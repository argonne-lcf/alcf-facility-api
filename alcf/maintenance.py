from functools import wraps
from fastapi import HTTPException
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from alcf.config import COMPONENT_MAINTENANCE_NOTICES
from alcf.enums import APIComponent


def require_component_operational(component: APIComponent):
    """
    Raises HTTPException with 503 Service Unavailable if the component is under maintenance.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):            
            for maintenance_notice in COMPONENT_MAINTENANCE_NOTICES:
                if maintenance_notice.component == component:
                    raise HTTPException(
                        status_code=HTTP_503_SERVICE_UNAVAILABLE,
                        detail=maintenance_notice.message
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
