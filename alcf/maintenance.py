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
            if COMPONENT_MAINTENANCE_NOTICES:
                if component in COMPONENT_MAINTENANCE_NOTICES:
                    raise HTTPException(
                        status_code=HTTP_503_SERVICE_UNAVAILABLE,
                        detail=COMPONENT_MAINTENANCE_NOTICES[component]
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
