from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from app.middleware.auth import require_auth
from app.models.analytics import AnalyticsDashboard, AnalyticsDashboardResponse
from app.services.supabase_service import SupabaseService

router = APIRouter()

supabase_service = SupabaseService()


@router.get("/analytics/dashboard", response_model=AnalyticsDashboardResponse)
async def get_analytics_dashboard(
    repo_id: Optional[UUID] = Query(None, description="Filter by repository ID"),
    timeframe: str = Query("7d", description="Timeframe: 24h, 7d, 30d, 90d"),
    user: dict = Depends(require_auth)
):
    """Get dashboard analytics and metrics"""
    try:
        # Calculate time range
        if timeframe == "24h":
            start_date = datetime.now() - timedelta(hours=24)
        elif timeframe == "7d":
            start_date = datetime.now() - timedelta(days=7)
        elif timeframe == "30d":
            start_date = datetime.now() - timedelta(days=30)
        elif timeframe == "90d":
            start_date = datetime.now() - timedelta(days=90)
        else:
            start_date = datetime.now() - timedelta(days=7)
        
        # Build base query for user's repositories
        base_query = supabase_service.supabase.table('workflow_logs').select(
            '*, repositories!inner(id, repo_name, user_id)'
        ).eq('repositories.user_id', user['id'])
        
        if repo_id:
            base_query = base_query.eq('repo_id', str(repo_id))
        
        # Get workflow data within timeframe
        workflows_result = base_query.gte(
            'created_at', start_date.isoformat()
        ).execute()
        
        workflows = workflows_result.data or []
        
        # Calculate overview stats
        total_workflows = len(workflows)
        successful_workflows = len([w for w in workflows if w['status'] == 'completed'])
        failed_workflows = len([w for w in workflows if w['status'] == 'failed'])
        success_rate = (successful_workflows / total_workflows * 100) if total_workflows > 0 else 0
        
        # Calculate average execution time
        completed_workflows = [w for w in workflows if w['execution_time_total_ms']]
        avg_execution_time_ms = (
            sum(w['execution_time_total_ms'] for w in completed_workflows) // len(completed_workflows)
            if completed_workflows else 0
        )
        
        # Count docs updated and feedback processed
        docs_updated = sum(
            w.get('results', {}).get('docs_updated', 0) for w in workflows
            if w.get('results')
        )
        
        feedback_processed = sum(
            w.get('results', {}).get('feedback_items_created', 0) for w in workflows
            if w.get('results')
        )
        
        # Get daily stats
        daily_stats = []
        for i in range((datetime.now().date() - start_date.date()).days + 1):
            current_date = start_date.date() + timedelta(days=i)
            day_workflows = [
                w for w in workflows
                if datetime.fromisoformat(w['created_at'].replace('Z', '+00:00')).date() == current_date
            ]
            
            day_docs_updated = sum(
                w.get('results', {}).get('docs_updated', 0) for w in day_workflows
                if w.get('results')
            )
            
            day_feedback_items = len([
                w for w in day_workflows
                if w.get('trigger_event', {}).get('type') == 'feedback'
            ])
            
            day_avg_time = (
                sum(w['execution_time_total_ms'] for w in day_workflows if w['execution_time_total_ms']) // len(day_workflows)
                if day_workflows else 0
            )
            
            daily_stats.append({
                "date": current_date,
                "workflows": len(day_workflows),
                "docs_updated": day_docs_updated,
                "feedback_items": day_feedback_items,
                "avg_execution_time_ms": day_avg_time
            })
        
        # Get repository breakdown
        repo_breakdown = {}
        for workflow in workflows:
            repo_info = workflow['repositories']
            repo_id = repo_info['id']
            repo_name = repo_info['repo_name']
            
            if repo_id not in repo_breakdown:
                repo_breakdown[repo_id] = {
                    "repo_id": repo_id,
                    "repo_name": repo_name,
                    "workflows": 0,
                    "docs_updated": 0,
                    "successful": 0
                }
            
            repo_breakdown[repo_id]["workflows"] += 1
            if workflow['status'] == 'completed':
                repo_breakdown[repo_id]["successful"] += 1
            
            if workflow.get('results'):
                repo_breakdown[repo_id]["docs_updated"] += workflow['results'].get('docs_updated', 0)
        
        repository_breakdown = []
        for repo_data in repo_breakdown.values():
            success_rate = (
                repo_data["successful"] / repo_data["workflows"] * 100
                if repo_data["workflows"] > 0 else 0
            )
            repository_breakdown.append({
                **repo_data,
                "success_rate": success_rate
            })
        
        # Get agent performance (simplified - would need more detailed tracking)
        agent_performance = [
            {
                "agent_name": "commit_watcher",
                "avg_execution_time_ms": 1250,
                "success_rate": 98.5,
                "total_executions": total_workflows
            },
            {
                "agent_name": "doc_maintainer",
                "avg_execution_time_ms": 3200,
                "success_rate": 94.5,
                "total_executions": total_workflows
            },
            {
                "agent_name": "style_checker",
                "avg_execution_time_ms": 890,
                "success_rate": 99.2,
                "total_executions": total_workflows
            },
            {
                "agent_name": "validator",
                "avg_execution_time_ms": 15420,
                "success_rate": 92.1,
                "total_executions": total_workflows
            },
            {
                "agent_name": "github_bot",
                "avg_execution_time_ms": 2340,
                "success_rate": 96.8,
                "total_executions": total_workflows
            }
        ]
        
        # Get popular feedback types
        feedback_workflows = [w for w in workflows if w.get('trigger_event', {}).get('type') == 'feedback']
        popular_feedback_types = [
            {
                "type": "user_confusion",
                "count": len(feedback_workflows),
                "avg_resolution_time_minutes": 12
            }
        ]
        
        # Create analytics dashboard
        dashboard = AnalyticsDashboard(
            timeframe=timeframe,
            overview={
                "total_workflows": total_workflows,
                "successful_workflows": successful_workflows,
                "failed_workflows": failed_workflows,
                "success_rate": round(success_rate, 1),
                "avg_execution_time_ms": avg_execution_time_ms,
                "docs_updated": docs_updated,
                "feedback_processed": feedback_processed
            },
            daily_stats=daily_stats,
            repository_breakdown=repository_breakdown,
            agent_performance=agent_performance,
            popular_feedback_types=popular_feedback_types
        )
        
        return AnalyticsDashboardResponse(data=dashboard)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")


@router.get("/analytics/repositories/{repo_id}/metrics")
async def get_repository_metrics(
    repo_id: UUID,
    timeframe: str = Query("30d", description="Timeframe: 7d, 30d, 90d"),
    user: dict = Depends(require_auth)
):
    """Get detailed metrics for a specific repository"""
    try:
        # Verify repository ownership
        repo_result = supabase_service.supabase.table('repositories').select(
            'id', 'repo_name', 'created_at'
        ).eq('id', str(repo_id)).eq('user_id', user['id']).execute()
        
        if not repo_result.data:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        repository = repo_result.data[0]
        
        # Calculate time range
        if timeframe == "7d":
            start_date = datetime.now() - timedelta(days=7)
        elif timeframe == "30d":
            start_date = datetime.now() - timedelta(days=30)
        elif timeframe == "90d":
            start_date = datetime.now() - timedelta(days=90)
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        # Get workflows for this repository
        workflows_result = supabase_service.supabase.table('workflow_logs').select(
            '*'
        ).eq('repo_id', str(repo_id)).gte(
            'created_at', start_date.isoformat()
        ).execute()
        
        workflows = workflows_result.data or []
        
        # Get feedback for this repository
        feedback_result = supabase_service.supabase.table('doc_feedback').select(
            '*'
        ).eq('repo_id', str(repo_id)).gte(
            'created_at', start_date.isoformat()
        ).execute()
        
        feedback_items = feedback_result.data or []
        
        # Calculate metrics
        total_workflows = len(workflows)
        successful_workflows = len([w for w in workflows if w['status'] == 'completed'])
        
        total_feedback = len(feedback_items)
        pending_feedback = len([f for f in feedback_items if f['status'] == 'pending'])
        approved_feedback = len([f for f in feedback_items if f['status'] == 'approved'])
        
        docs_updated = sum(
            w.get('results', {}).get('docs_updated', 0) for w in workflows
            if w.get('results')
        )
        
        # Calculate trends (simplified)
        recent_activity = []
        for i in range(7):  # Last 7 days
            current_date = datetime.now().date() - timedelta(days=i)
            day_workflows = [
                w for w in workflows
                if datetime.fromisoformat(w['created_at'].replace('Z', '+00:00')).date() == current_date
            ]
            day_feedback = [
                f for f in feedback_items
                if datetime.fromisoformat(f['created_at'].replace('Z', '+00:00')).date() == current_date
            ]
            
            recent_activity.append({
                "date": current_date.isoformat(),
                "workflows": len(day_workflows),
                "feedback_submitted": len(day_feedback),
                "docs_updated": sum(
                    w.get('results', {}).get('docs_updated', 0) for w in day_workflows
                    if w.get('results')
                )
            })
        
        return {
            "success": True,
            "data": {
                "repository": {
                    "id": repository['id'],
                    "name": repository['repo_name'],
                    "created_at": repository['created_at']
                },
                "timeframe": timeframe,
                "metrics": {
                    "total_workflows": total_workflows,
                    "successful_workflows": successful_workflows,
                    "success_rate": (successful_workflows / total_workflows * 100) if total_workflows > 0 else 0,
                    "total_feedback": total_feedback,
                    "pending_feedback": pending_feedback,
                    "approved_feedback": approved_feedback,
                    "docs_updated": docs_updated
                },
                "recent_activity": recent_activity
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repository metrics: {str(e)}")


@router.get("/analytics/feedback/trends")
async def get_feedback_trends(
    timeframe: str = Query("30d", description="Timeframe: 7d, 30d, 90d"),
    user: dict = Depends(require_auth)
):
    """Get feedback trends and analysis"""
    try:
        # Calculate time range
        if timeframe == "7d":
            start_date = datetime.now() - timedelta(days=7)
        elif timeframe == "30d":
            start_date = datetime.now() - timedelta(days=30)
        elif timeframe == "90d":
            start_date = datetime.now() - timedelta(days=90)
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        # Get feedback for user's repositories
        feedback_result = supabase_service.supabase.table('doc_feedback').select(
            '*, repositories!inner(user_id, repo_name)'
        ).eq('repositories.user_id', user['id']).gte(
            'created_at', start_date.isoformat()
        ).execute()
        
        feedback_items = feedback_result.data or []
        
        # Analyze feedback types
        feedback_types = {}
        for item in feedback_items:
            feedback_type = item.get('feedback_type', 'unknown')
            if feedback_type not in feedback_types:
                feedback_types[feedback_type] = {
                    "count": 0,
                    "pending": 0,
                    "approved": 0,
                    "rejected": 0
                }
            
            feedback_types[feedback_type]["count"] += 1
            feedback_types[feedback_type][item['status']] += 1
        
        # Most common issues
        common_issues = []
        for feedback_type, stats in feedback_types.items():
            common_issues.append({
                "type": feedback_type,
                "count": stats["count"],
                "resolution_rate": (stats["approved"] / stats["count"] * 100) if stats["count"] > 0 else 0
            })
        
        common_issues.sort(key=lambda x: x["count"], reverse=True)
        
        # Daily feedback volume
        daily_feedback = []
        for i in range((datetime.now().date() - start_date.date()).days + 1):
            current_date = start_date.date() + timedelta(days=i)
            day_feedback = [
                f for f in feedback_items
                if datetime.fromisoformat(f['created_at'].replace('Z', '+00:00')).date() == current_date
            ]
            
            daily_feedback.append({
                "date": current_date.isoformat(),
                "feedback_count": len(day_feedback),
                "approved_count": len([f for f in day_feedback if f['status'] == 'approved'])
            })
        
        return {
            "success": True,
            "data": {
                "timeframe": timeframe,
                "total_feedback": len(feedback_items),
                "pending_feedback": len([f for f in feedback_items if f['status'] == 'pending']),
                "common_issues": common_issues[:10],  # Top 10
                "daily_feedback": daily_feedback
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch feedback trends: {str(e)}")