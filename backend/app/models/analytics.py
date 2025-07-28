from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from uuid import UUID

from .base import BaseResponse


class OverviewStats(BaseModel):
    total_workflows: int = 0
    successful_workflows: int = 0
    failed_workflows: int = 0
    success_rate: float = 0.0
    avg_execution_time_ms: int = 0
    docs_updated: int = 0
    feedback_processed: int = 0


class DailyStats(BaseModel):
    date: date
    workflows: int = 0
    docs_updated: int = 0
    feedback_items: int = 0
    avg_execution_time_ms: int = 0


class RepositoryBreakdown(BaseModel):
    repo_id: UUID
    repo_name: str
    workflows: int = 0
    docs_updated: int = 0
    success_rate: float = 0.0


class AgentPerformance(BaseModel):
    agent_name: str
    avg_execution_time_ms: int = 0
    success_rate: float = 0.0
    total_executions: int = 0


class PopularFeedbackType(BaseModel):
    type: str
    count: int = 0
    avg_resolution_time_minutes: int = 0


class AnalyticsDashboard(BaseModel):
    timeframe: str
    overview: OverviewStats
    daily_stats: List[DailyStats] = Field(default_factory=list)
    repository_breakdown: List[RepositoryBreakdown] = Field(default_factory=list)
    agent_performance: List[AgentPerformance] = Field(default_factory=list)
    popular_feedback_types: List[PopularFeedbackType] = Field(default_factory=list)


class AnalyticsDashboardResponse(BaseResponse):
    data: AnalyticsDashboard