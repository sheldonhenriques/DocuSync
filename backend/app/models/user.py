from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from .base import BaseResponse, PaginationResponse


class UserPreferences(BaseModel):
    email_notifications: bool = True
    slack_notifications: bool = False
    auto_approve_low_risk: bool = True
    dashboard_refresh_interval: int = 30


class UserSubscription(BaseModel):
    plan: str = "free"  # free, pro, enterprise
    repositories_limit: int = 3
    current_repositories: int = 0
    workflows_per_month_limit: int = 100
    workflows_this_month: int = 0


class User(BaseModel):
    id: UUID
    github_id: int
    username: str
    email: str
    avatar_url: Optional[str] = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    subscription: UserSubscription = Field(default_factory=UserSubscription)
    created_at: datetime


class UserResponse(BaseResponse):
    data: User


class UpdateUserPreferencesRequest(BaseModel):
    preferences: UserPreferences


class UpdateUserPreferencesResponse(BaseResponse):
    data: UserPreferences