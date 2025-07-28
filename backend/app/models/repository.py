from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

from .base import BaseResponse, PaginationResponse


class NotificationSettings(BaseModel):
    slack_webhook: Optional[str] = None
    email_notifications: bool = True


class DocConfig(BaseModel):
    watch_patterns: List[str] = Field(default=["*.py", "*.md", "api/**"])
    ignore_patterns: List[str] = Field(default=["node_modules/**", "*.pyc"])
    doc_root: str = "docs/"
    auto_approve: bool = False
    notification_settings: NotificationSettings = Field(default_factory=NotificationSettings)


class RepositoryStats(BaseModel):
    total_docs: int = 0
    pending_updates: int = 0
    last_workflow_run: Optional[datetime] = None


class Repository(BaseModel):
    id: UUID
    github_repo_id: int
    repo_name: str
    owner: str
    full_name: str
    doc_config: DocConfig
    status: str = "active"  # active, paused, error
    last_sync: Optional[datetime] = None
    stats: RepositoryStats = Field(default_factory=RepositoryStats)
    created_at: datetime
    updated_at: datetime


class CreateRepositoryRequest(BaseModel):
    github_repo_url: str
    doc_config: Optional[DocConfig] = None


class CreateRepositoryResponse(BaseResponse):
    data: Dict[str, Any]


class UpdateRepositoryConfigRequest(BaseModel):
    doc_config: DocConfig


class UpdateRepositoryConfigResponse(BaseResponse):
    data: Repository


class RepositoryListResponse(BaseResponse):
    data: List[Repository]
    pagination: PaginationResponse


class RepositoryResponse(BaseResponse):
    data: Repository