from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

from .base import BaseResponse, PaginationResponse


class ValidationResults(BaseModel):
    code_examples: Dict[str, Any] = Field(default_factory=dict)
    links_valid: bool = True
    formatting_valid: bool = True


class TriggeredBy(BaseModel):
    type: str  # user_feedback, code_change, pr_review
    user_id: Optional[UUID] = None
    event_id: Optional[str] = None


class AgentResponse(BaseModel):
    agent: str
    status: str
    execution_time_ms: int


class WorkflowInfo(BaseModel):
    orkes_workflow_id: Optional[str] = None
    orkes_execution_id: Optional[str] = None
    agent_responses: List[AgentResponse] = Field(default_factory=list)


class Feedback(BaseModel):
    id: UUID
    repo_id: UUID
    repo_name: str
    file_path: str
    section: Optional[str] = None
    feedback_type: str  # user_confusion, code_change, validation_error
    feedback_text: str
    suggestion: Optional[str] = None
    validation_results: Optional[ValidationResults] = None
    confidence_score: Optional[float] = None
    priority: str = "medium"  # high, medium, low
    status: str = "pending"  # pending, approved, rejected
    triggered_by: Optional[TriggeredBy] = None
    workflow_info: Optional[WorkflowInfo] = None
    created_at: datetime
    updated_at: datetime


class SubmitFeedbackRequest(BaseModel):
    repo_id: UUID
    file_path: str
    section: Optional[str] = None
    feedback_text: str
    page_url: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None


class SubmitFeedbackResponse(BaseResponse):
    data: Dict[str, Any]


class ApproveFeedbackRequest(BaseModel):
    approved_content: Optional[str] = None
    commit_message: Optional[str] = None
    auto_commit: bool = True


class ApproveFeedbackResponse(BaseResponse):
    data: Dict[str, Any]


class RejectFeedbackRequest(BaseModel):
    reason: str  # suggestion_incorrect, out_of_scope, duplicate
    notes: Optional[str] = None


class RejectFeedbackResponse(BaseResponse):
    data: Dict[str, Any]


class FeedbackListResponse(BaseResponse):
    data: List[Feedback]
    pagination: PaginationResponse


class FeedbackResponse(BaseResponse):
    data: Feedback