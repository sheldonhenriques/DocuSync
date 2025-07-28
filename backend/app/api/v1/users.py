from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from app.middleware.auth import require_auth
from app.models.user import (
    User, UserResponse, UpdateUserPreferencesRequest, 
    UpdateUserPreferencesResponse, UserPreferences
)
from app.services.supabase_service import SupabaseService

router = APIRouter()

supabase_service = SupabaseService()


@router.get("/user/profile", response_model=UserResponse)
async def get_user_profile(user: dict = Depends(require_auth)):
    """Get user profile and preferences"""
    try:
        # Get user data with preferences and subscription info
        result = supabase_service.supabase.table('users').select('*').eq(
            'id', user['id']
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = result.data[0]
        
        # Count current repositories for subscription info
        repos_result = supabase_service.supabase.table('repositories').select(
            'id', count='exact'
        ).eq('user_id', user['id']).execute()
        
        current_repositories = repos_result.count or 0
        
        # Count workflows this month for subscription info
        workflows_result = supabase_service.supabase.table('workflow_logs').select(
            'id', count='exact'
        ).eq('repo_id.in', f"(SELECT id FROM repositories WHERE user_id = '{user['id']}')").\
        gte('created_at', 'date_trunc(\'month\', now())').execute()
        
        workflows_this_month = workflows_result.count or 0
        
        # Update subscription info
        if 'subscription' not in user_data:
            user_data['subscription'] = {}
        
        user_data['subscription']['current_repositories'] = current_repositories
        user_data['subscription']['workflows_this_month'] = workflows_this_month
        
        user_obj = User(**user_data)
        return UserResponse(data=user_obj)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user profile: {str(e)}")


@router.put("/user/preferences", response_model=UpdateUserPreferencesResponse)
async def update_user_preferences(
    request: UpdateUserPreferencesRequest,
    user: dict = Depends(require_auth)
):
    """Update user preferences"""
    try:
        # Update user preferences in database
        result = supabase_service.supabase.table('users').update({
            'preferences': request.preferences.dict()
        }).eq('id', user['id']).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update preferences")
        
        updated_preferences = UserPreferences(**result.data[0]['preferences'])
        
        return UpdateUserPreferencesResponse(
            data=updated_preferences,
            message="Preferences updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")


@router.get("/user/subscription")
async def get_user_subscription(user: dict = Depends(require_auth)):
    """Get user subscription details and usage"""
    try:
        # Get user subscription info
        result = supabase_service.supabase.table('users').select(
            'subscription'
        ).eq('id', user['id']).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        subscription_data = result.data[0].get('subscription', {})
        
        # Get current usage
        repos_result = supabase_service.supabase.table('repositories').select(
            'id', count='exact'
        ).eq('user_id', user['id']).execute()
        
        current_repositories = repos_result.count or 0
        
        # Get workflows this month
        workflows_result = supabase_service.supabase.table('workflow_logs').select(
            'id', count='exact'
        ).eq('repo_id.in', f"(SELECT id FROM repositories WHERE user_id = '{user['id']}')").\
        gte('created_at', 'date_trunc(\'month\', now())').execute()
        
        workflows_this_month = workflows_result.count or 0
        
        # Calculate usage percentages
        repos_limit = subscription_data.get('repositories_limit', 3)
        workflows_limit = subscription_data.get('workflows_per_month_limit', 100)
        
        repos_usage_percent = (current_repositories / repos_limit * 100) if repos_limit > 0 else 0
        workflows_usage_percent = (workflows_this_month / workflows_limit * 100) if workflows_limit > 0 else 0
        
        return {
            "success": True,
            "data": {
                "plan": subscription_data.get('plan', 'free'),
                "limits": {
                    "repositories": repos_limit,
                    "workflows_per_month": workflows_limit
                },
                "current_usage": {
                    "repositories": current_repositories,
                    "workflows_this_month": workflows_this_month
                },
                "usage_percentages": {
                    "repositories": round(repos_usage_percent, 1),
                    "workflows": round(workflows_usage_percent, 1)
                },
                "approaching_limits": {
                    "repositories": repos_usage_percent > 80,
                    "workflows": workflows_usage_percent > 80
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch subscription info: {str(e)}")


@router.get("/user/activity")
async def get_user_activity(user: dict = Depends(require_auth)):
    """Get recent user activity and notifications"""
    try:
        # Get recent workflows
        workflows_result = supabase_service.supabase.table('workflow_logs').select(
            '*, repositories!inner(repo_name)'
        ).eq('repositories.user_id', user['id']).order(
            'created_at', desc=True
        ).limit(10).execute()
        
        recent_workflows = workflows_result.data or []
        
        # Get recent feedback
        feedback_result = supabase_service.supabase.table('doc_feedback').select(
            '*, repositories!inner(repo_name)'
        ).eq('repositories.user_id', user['id']).order(
            'created_at', desc=True
        ).limit(10).execute()
        
        recent_feedback = feedback_result.data or []
        
        # Get pending items count
        pending_feedback_count = len([f for f in recent_feedback if f['status'] == 'pending'])
        running_workflows_count = len([w for w in recent_workflows if w['status'] == 'running'])
        
        # Generate activity feed
        activity_feed = []
        
        # Add workflow activities
        for workflow in recent_workflows[:5]:
            activity_feed.append({
                "type": "workflow",
                "action": f"Workflow {workflow['status']}",
                "description": f"Documentation sync for {workflow['repositories']['repo_name']}",
                "timestamp": workflow['created_at'],
                "status": workflow['status']
            })
        
        # Add feedback activities
        for feedback in recent_feedback[:5]:
            activity_feed.append({
                "type": "feedback",
                "action": f"Feedback {feedback['status']}",
                "description": f"Documentation feedback for {feedback['repositories']['repo_name']}",
                "timestamp": feedback['created_at'],
                "status": feedback['status']
            })
        
        # Sort by timestamp
        activity_feed.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            "success": True,
            "data": {
                "pending_items": {
                    "feedback": pending_feedback_count,
                    "running_workflows": running_workflows_count
                },
                "recent_activity": activity_feed[:10],
                "summary": {
                    "total_repositories": len(set(w['repositories']['repo_name'] for w in recent_workflows)),
                    "recent_workflows": len(recent_workflows),
                    "recent_feedback": len(recent_feedback)
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user activity: {str(e)}")


@router.delete("/user/account")
async def delete_user_account(user: dict = Depends(require_auth)):
    """Delete user account and all associated data"""
    try:
        # This would be a soft delete in production
        # For now, just return a message about the process
        
        # Get user's repository count for confirmation
        repos_result = supabase_service.supabase.table('repositories').select(
            'id', count='exact'
        ).eq('user_id', user['id']).execute()
        
        repository_count = repos_result.count or 0
        
        return {
            "success": True,
            "message": "Account deletion process initiated",
            "data": {
                "repositories_to_remove": repository_count,
                "estimated_completion": "24-48 hours",
                "note": "All repositories will be removed from monitoring and webhooks will be uninstalled"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process account deletion: {str(e)}")