from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class BaseLog(BaseModel):
    id: str
    api_route: str
    status_code: Optional[int] = Field(default=None)
    input: Dict[Any, Any]
    error: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    @classmethod
    def has_field(cls, field_name: str) -> bool:
        return field_name in cls.model_fields
    

class AuthenticatedBaseLog(BaseLog):
    user_id: str
    user_name: str
    ip: str


class AuthenticateComputeLog(AuthenticatedBaseLog):
    resource_id: str
    alcf_username: str
    response: Optional[Dict[Any, Any]] = Field(default=None)


class AccountLog(BaseLog):
    response: Optional[Dict[Any, Any]] = Field(default=None)


class AuthenticatedAccountLog(AuthenticatedBaseLog):
    response: Optional[Dict[Any, Any]] = Field(default=None)
