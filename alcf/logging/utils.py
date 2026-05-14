import inspect
from starlette.status import HTTP_200_OK
from typing import Dict, Any
from fastapi import HTTPException
from alcf.logging.schemas import BaseLog
from alcf.logging.service import log_service


def get_input_from_func(func, *args, **kwargs) -> Dict:
    """Inspect the signature of a function and generate a dictionary with all inputs"""
    
    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()
    
    input_data = dict(bound_args.arguments)
    input_data.pop('self', None)
    
    return input_data


async def run_and_log(
    log: BaseLog,
    func, *args, **kwargs
) -> Any:
    """Run function and log the outcome."""
    
    try:
        result = await func(*args, **kwargs)
        log.status_code = HTTP_200_OK
        if log.has_field("response"):
            log.response = result
        log_service.handle_log(log)
        return result
             
    except HTTPException as e:
        log.status_code = e.status_code
        log.error = str(e.detail)
        log_service.handle_log(log)
        raise