from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from uuid import UUID

from app.middleware.auth import require_auth
from app.models.workflow import Workflow, WorkflowListResponse, WorkflowResponse
from app.models.base import PaginationParams, PaginationResponse
from app.middleware.error_handler import WorkflowError
from app.services.supabase_service import SupabaseService
from app.services.orkes_service import OrkesService

router = APIRouter()

supabase_service = SupabaseService()
orkes_service = OrkesService()


@router.get("/workflows", response_model=WorkflowListResponse)
async def get_workflows(
    repo_id: Optional[UUID] = Query(None, description="Filter by repository ID"),
    status: Optional[str] = Query(None, description="Filter by status: running, completed, failed, all"),
    trigger_type: Optional[str] = Query(None, description="Filter by trigger: pr, commit, feedback, manual"),
    pagination: PaginationParams = Depends(),
    user: dict = Depends(require_auth)
):
    """Get workflow execution history and status"""
    try:
        # Build query to get workflows for user's repositories
        query = supabase_service.supabase.table('workflow_logs').select(
            '*, repositories!inner(repo_name, user_id)', count='exact'
        )
        
        # Filter by user's repositories
        query = query.eq('repositories.user_id', user['id'])
        
        # Apply filters
        if repo_id:
            query = query.eq('repo_id', str(repo_id))
        
        if status and status != 'all':
            query = query.eq('status', status)
        
        if trigger_type:
            # Filter by trigger event type
            query = query.contains('trigger_event', {'type': trigger_type})
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.per_page
        query = query.range(offset, offset + pagination.per_page - 1)
        query = query.order('created_at', desc=True)
        
        result = query.execute()
        
        # Transform data to include repo_name
        workflows = []
        for item in result.data:
            workflow_data = {**item}
            workflow_data['repo_name'] = item['repositories']['repo_name']
            del workflow_data['repositories']  # Remove nested object
            workflows.append(Workflow(**workflow_data))
        
        total_count = result.count or 0
        total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
        
        pagination_response = PaginationResponse(
            page=pagination.page,
            per_page=pagination.per_page,
            total=total_count,
            total_pages=total_pages
        )
        
        return WorkflowListResponse(
            data=workflows,
            pagination=pagination_response
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch workflows: {str(e)}")


@router.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    user: dict = Depends(require_auth)
):
    """Get specific workflow by ID"""
    try:
        result = supabase_service.supabase.table('workflow_logs').select(
            '*, repositories!inner(repo_name, user_id)'
        ).eq('id', str(workflow_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        item = result.data[0]
        
        # Verify user owns the repository
        if item['repositories']['user_id'] != user['id']:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow_data = {**item}
        workflow_data['repo_name'] = item['repositories']['repo_name']
        del workflow_data['repositories']
        
        workflow = Workflow(**workflow_data)
        return WorkflowResponse(data=workflow)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch workflow: {str(e)}")


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: UUID,
    user: dict = Depends(require_auth)
):
    """Cancel a running workflow"""
    try:
        # Get workflow and verify ownership
        result = supabase_service.supabase.table('workflow_logs').select(
            '*, repositories!inner(user_id)'
        ).eq('id', str(workflow_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow_item = result.data[0]
        
        # Verify user owns the repository
        if workflow_item['repositories']['user_id'] != user['id']:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Check if workflow is still running
        if workflow_item['status'] not in ['running']:
            raise HTTPException(status_code=400, detail="Workflow is not running")
        
        # Cancel workflow in Orkes
        success = await orkes_service.cancel_workflow(
            workflow_item['orkes_execution_id']
        )
        
        if not success:
            raise WorkflowError("Failed to cancel workflow", workflow_item['orkes_execution_id'])
        
        # Update status in database
        supabase_service.supabase.table('workflow_logs').update({
            'status': 'cancelled',
            'completed_at': 'now()'
        }).eq('id', str(workflow_id)).execute()
        
        return {
            "success": True,
            "message": "Workflow cancelled successfully"
        }
        
    except HTTPException:
        raise
    except WorkflowError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel workflow: {str(e)}")


@router.post("/workflows/{workflow_id}/retry")
async def retry_workflow(
    workflow_id: UUID,
    user: dict = Depends(require_auth)
):
    """Retry a failed workflow"""
    try:
        # Get workflow and verify ownership
        result = supabase_service.supabase.table('workflow_logs').select(
            '*, repositories!inner(user_id, repo_name, owner)'
        ).eq('id', str(workflow_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow_item = result.data[0]
        
        # Verify user owns the repository
        if workflow_item['repositories']['user_id'] != user['id']:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Check if workflow can be retried
        if workflow_item['status'] not in ['failed', 'cancelled']:
            raise HTTPException(status_code=400, detail="Workflow cannot be retried")
        
        repo = workflow_item['repositories']
        
        # Start new workflow with same trigger event
        new_workflow_id = await orkes_service.retry_workflow(
            original_workflow_id=workflow_item['orkes_workflow_id'],
            trigger_event=workflow_item['trigger_event'],
            repo_info={
                'id': workflow_item['repo_id'],
                'name': repo['repo_name'],
                'owner': repo['owner']
            }
        )
        
        return {
            "success": True,
            "new_workflow_id": new_workflow_id,
            "message": "Workflow retry initiated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retry workflow: {str(e)}")


@router.get("/workflows/{workflow_id}/logs")
async def get_workflow_logs(
    workflow_id: UUID,
    user: dict = Depends(require_auth)
):
    """Get detailed logs for a specific workflow"""
    try:
        # Get workflow and verify ownership
        result = supabase_service.supabase.table('workflow_logs').select(
            '*, repositories!inner(user_id)'
        ).eq('id', str(workflow_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow_item = result.data[0]
        
        # Verify user owns the repository
        if workflow_item['repositories']['user_id'] != user['id']:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Get detailed logs from Orkes
        detailed_logs = await orkes_service.get_workflow_execution_logs(
            workflow_item['orkes_execution_id']
        )
        
        return {
            "success": True,
            "data": {
                "workflow_id": str(workflow_id),
                "orkes_execution_id": workflow_item['orkes_execution_id'],
                "status": workflow_item['status'],
                "logs": detailed_logs
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch workflow logs: {str(e)}")


@router.get("/workflows/stats/summary")
async def get_workflow_summary_stats(
    user: dict = Depends(require_auth),
    timeframe: str = Query("7d", description="Timeframe: 24h, 7d, 30d")
):
    """Get summary statistics for user's workflows"""
    try:
        # Calculate timeframe
        if timeframe == "24h":
            time_filter = "created_at >= now() - interval '24 hours'"
        elif timeframe == "7d":
            time_filter = "created_at >= now() - interval '7 days'"
        elif timeframe == "30d":
            time_filter = "created_at >= now() - interval '30 days'"
        else:
            time_filter = "created_at >= now() - interval '7 days'"
        
        # Get workflow counts by status
        status_query = f"""
            SELECT 
                status,
                COUNT(*) as count,
                AVG(execution_time_total_ms) as avg_execution_time
            FROM workflow_logs w
            JOIN repositories r ON w.repo_id = r.id
            WHERE r.user_id = '{user['id']}' AND {time_filter}
            GROUP BY status
        """
        
        # Execute raw SQL query (Note: In production, use proper query builder)
        # This is a simplified version - implement proper query execution
        
        # For now, return mock data structure
        summary_stats = {
            "timeframe": timeframe,
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "running_workflows": 0,
            "success_rate": 0.0,
            "avg_execution_time_ms": 0
        }
        
        return {
            "success": True,
            "data": summary_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch workflow stats: {str(e)}")