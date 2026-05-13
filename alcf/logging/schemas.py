from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import uuid4


# Non-authenticated base models
# =============================

class BaseLog(BaseModel):
    id: Optional[str] = Field(default=str(uuid4()))
    api_function: str
    status_code: Optional[int] = Field(default=None)
    input: Dict[Any, Any]
    error: Optional[str] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    @classmethod
    def has_field(cls, field_name: str) -> bool:
        return field_name in cls.model_fields


class BaseLogWithResponse(BaseLog):
    response: Optional[Dict[Any, Any]] = Field(default=None)


# Authenticated base models
# =========================

class AutheBaseLog(BaseLog):
    user_id: str
    user_name: str
    ip: str


class AuthBaseLogWithResponse(AutheBaseLog):
    response: Optional[Dict[Any, Any]] = Field(default=None)


# API component log models
# ========================

class StatusLog(BaseLog):
    stream: Optional[str] = Field(default="status")


class FacilityLog(BaseLog):
    stream: Optional[str] = Field(default="facility")


class AuthComputeLog(AuthBaseLogWithResponse):
    resource_id: str
    alcf_username: str
    stream: Optional[str] = Field(default="compute")


class AuthFilesystemLog(AuthBaseLogWithResponse):
    resource_id: str
    stream: Optional[str] = Field(default="filesystem")


class AccountLog(BaseLogWithResponse):
    stream: Optional[str] = Field(default="account")


class AuthAccountLog(AuthBaseLogWithResponse):
    stream: Optional[str] = Field(default="account")

