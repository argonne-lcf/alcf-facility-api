from uuid import uuid4

from pydantic import BaseModel, Field
from typing import Optional, Any


class GlobusSubmitResponse(BaseModel):
    task_id: Optional[str] = Field(default=str(uuid4()))
    result: Optional[Any] = Field(default=None)
    failed: Optional[bool] = Field(default=False)