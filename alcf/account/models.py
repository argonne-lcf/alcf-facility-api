from datetime import datetime, timezone
from pydantic import BaseModel, field_validator, Field
from typing import List, Optional

from app.routers.account.models import AllocationUnit


class NiProject(BaseModel):
    id: str
    name: str
    users: List[str]
    resources: List[str]
    description: Optional[str] = Field(default="N/A")
    last_modified: Optional[datetime] = Field(default=datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc))


class NiAllocation(BaseModel):
    allocation_id: str
    resource: str
    project: str
    balance: int
    deposits: int

    @property
    def used(self) -> int:
        return self.deposits - self.balance
    
    @field_validator("allocation_id", mode="before")
    @classmethod
    def format_allocation_id(cls, value):
        return str(value)
    

class NiCapability(BaseModel):
    name: str
    units: List[str]
    description: Optional[str] = Field(default="N/A")
    last_updated: Optional[datetime] = Field(default=datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc))

    @field_validator("units", mode="after")
    @classmethod
    def format_units(cls, value):
        formatted_units = []
        for ni_unit in value:
            if ni_unit == "Node Hours":
                formatted_units.append(AllocationUnit.node_hours.value)
            elif ni_unit == "TB": # TODO: need to handle the conversion, add TB in IRI, or receive bytes
                formatted_units.append(AllocationUnit.bytes.value)
            else:
                raise ValueError(f"Cannot format allocation unit. {ni_unit} not supported.")
        return formatted_units
    

class NiProjects(BaseModel):
    projects: List[NiProject]


class NiAllocations(BaseModel):
    allocations: List[NiAllocation]


class NiCapabilities(BaseModel):
    capabilities: List[NiCapability]