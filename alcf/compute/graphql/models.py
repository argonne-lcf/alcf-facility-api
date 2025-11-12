from pydantic import BaseModel
from typing import List, Optional

class JobTasksResources(BaseModel):
    index: Optional[str] = ""
    wallClockTime: Optional[int] = None
    physicalMemory: Optional[int] = None

class JobResources(BaseModel):
    peName: Optional[str] = None
    jobResources: Optional[JobTasksResources] = JobTasksResources()

class JobStatus(BaseModel):
    state: Optional[int] = None
    exitStatus: Optional[int] = None

class Queue(BaseModel):
    name: Optional[str] = None

class Job(BaseModel):
    jobId: Optional[str] = None
    status: Optional[JobStatus] = None
    owner: Optional[str] = None
    remoteCommand: Optional[str] = None
    commandArgs: Optional[List[str]] = None
    workDir: Optional[str] = None
    resourcesRequested: Optional[JobResources] = None
    resourcesUsed: Optional[JobResources] = None
    queue: Optional[Queue] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    submitTime: Optional[str] = None
    name: Optional[str] = None
    errorPath: Optional[str] = None
    outputPath: Optional[str] = None

class ErrorResponse(BaseModel):
    errorCode: int
    errorMessage: str

class JobResponse(BaseModel):
    node: Optional[Job] = None
    error: Optional[ErrorResponse] = None

class QueryJobsFilter(BaseModel):
    withHistoryJobs: Optional[bool] = False
    jobIds: Optional[str] = None
