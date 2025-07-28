from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

from .base import BaseResponse, PaginationResponse


class TriggerEvent(BaseModel):
    type: str  # pull_request, push, feedback, manual
    github_event_id: Optional[str] = None
    pr_number: Optional[int] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None


class WorkflowProgress(BaseModel):
    current_step: str
    total_steps: int
    completed_steps: int


class AgentExecution(BaseModel):
    agent_name: str
    status: str  # running, completed, failed
    execution_time_ms: Optional[int] = None
    output_summary: Optional[str] = None
    daytona_workspace_url: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowResults(BaseModel):
    docs_updated: int = 0
    validation_passed: bool = True
    github_comment_posted: bool = False
    feedback_items_created: int = 0


class Workflow(BaseModel):
    id: UUID
    orkes_workflow_id: str
    orkes_execution_id: str
    repo_id: UUID
    repo_name: str
    trigger_event: TriggerEvent
    status: str  # running, completed, failed, cancelled
    progress: Optional[WorkflowProgress] = None
    agents_executed: List[AgentExecution] = Field(default_factory=list)
    results: Optional[WorkflowResults] = None
    execution_time_total_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class WorkflowListResponse(BaseResponse):
    data: List[Workflow]
    pagination: Optional[PaginationResponse] = None


class WorkflowResponse(BaseResponse):
    data: Workflow