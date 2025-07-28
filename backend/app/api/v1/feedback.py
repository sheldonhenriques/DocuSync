from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from uuid import UUID

from app.middleware.auth import require_auth, optional_auth
from app.models.feedback import (
    Feedback, SubmitFeedbackRequest, SubmitFeedbackResponse,
    ApproveFeedbackRequest, ApproveFeedbackResponse,
    RejectFeedbackRequest, RejectFeedbackResponse,
    FeedbackListResponse, FeedbackResponse
)
from app.models.base import PaginationParams, PaginationResponse
from app.middleware.error_handler import FeedbackNotFoundError, RepositoryNotFoundError
from app.services.supabase_service import SupabaseService
from app.services.github_service import GitHubService
from app.services.orkes_service import OrkesService

router = APIRouter()

supabase_service = SupabaseService()
github_service = GitHubService()
orkes_service = OrkesService()


@router.get("/feedback", response_model=FeedbackListResponse)
async def get_feedback(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, all"),
    repo_id: Optional[UUID] = Query(None, description="Filter by repository ID"),
    pagination: PaginationParams = Depends(),
    user: dict = Depends(require_auth)
):
    """Get pending documentation feedback/suggestions"""
    try:
        # Build query
        query = supabase_service.supabase.table('doc_feedback').select(
            '*, repositories!inner(repo_name)', count='exact'
        )
        
        # Filter by user's repositories
        query = query.eq('repositories.user_id', user['id'])
        
        # Apply filters
        if status and status != 'all':
            query = query.eq('status', status)
        
        if repo_id:
            query = query.eq('repo_id', str(repo_id))
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.per_page
        query = query.range(offset, offset + pagination.per_page - 1)
        query = query.order('created_at', desc=True)
        
        result = query.execute()
        
        # Transform data to include repo_name
        feedback_items = []
        for item in result.data:
            feedback_data = {**item}
            feedback_data['repo_name'] = item['repositories']['repo_name']
            del feedback_data['repositories']  # Remove nested object
            feedback_items.append(Feedback(**feedback_data))
        
        total_count = result.count or 0
        total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
        
        pagination_response = PaginationResponse(
            page=pagination.page,
            per_page=pagination.per_page,
            total=total_count,
            total_pages=total_pages
        )
        
        return FeedbackListResponse(
            data=feedback_items,
            pagination=pagination_response
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch feedback: {str(e)}")


@router.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_item(
    feedback_id: UUID,
    user: dict = Depends(require_auth)
):
    """Get specific feedback item by ID"""
    try:
        result = supabase_service.supabase.table('doc_feedback').select(
            '*, repositories!inner(repo_name, user_id)'
        ).eq('id', str(feedback_id)).execute()
        
        if not result.data:
            raise FeedbackNotFoundError(str(feedback_id))
        
        item = result.data[0]
        
        # Verify user owns the repository
        if item['repositories']['user_id'] != user['id']:
            raise FeedbackNotFoundError(str(feedback_id))
        
        feedback_data = {**item}
        feedback_data['repo_name'] = item['repositories']['repo_name']
        del feedback_data['repositories']
        
        feedback = Feedback(**feedback_data)
        return FeedbackResponse(data=feedback)
        
    except FeedbackNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch feedback: {str(e)}")


@router.post("/feedback/submit", response_model=SubmitFeedbackResponse)
async def submit_feedback(
    request: SubmitFeedbackRequest,
    user: Optional[dict] = Depends(optional_auth)
):
    """Submit reader feedback from documentation site"""
    try:
        # Verify repository exists
        repo_result = supabase_service.supabase.table('repositories').select(
            'id', 'repo_name', 'owner'
        ).eq('id', str(request.repo_id)).execute()
        
        if not repo_result.data:
            raise RepositoryNotFoundError(str(request.repo_id))
        
        repo = repo_result.data[0]
        
        # Create feedback record
        feedback_data = {
            'repo_id': str(request.repo_id),
            'file_path': request.file_path,
            'section': request.section,
            'feedback_type': 'user_confusion',  # Default type for submitted feedback
            'feedback_text': request.feedback_text,
            'status': 'pending',
            'triggered_by': {
                'type': 'user_feedback',
                'user_id': user['id'] if user else None,
                'page_url': request.page_url,
                'user_context': request.user_context
            }
        }
        
        result = supabase_service.supabase.table('doc_feedback').insert(
            feedback_data
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to submit feedback")
        
        feedback_record = result.data[0]
        
        # Trigger feedback processing workflow
        workflow_id = await orkes_service.trigger_feedback_workflow(
            feedback_id=feedback_record['id'],
            repo_info={
                'id': repo['id'],
                'name': repo['repo_name'],
                'owner': repo['owner']
            },
            feedback_data=feedback_data
        )
        
        return SubmitFeedbackResponse(
            data={
                "feedback_id": feedback_record['id'],
                "estimated_response_time": "2-5 minutes",
                "workflow_triggered": bool(workflow_id),
                "orkes_workflow_id": workflow_id
            },
            message="Thank you for your feedback! Our AI agents are working on an improved explanation."
        )
        
    except RepositoryNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@router.post("/feedback/{feedback_id}/approve", response_model=ApproveFeedbackResponse)
async def approve_feedback(
    feedback_id: UUID,
    request: ApproveFeedbackRequest,
    user: dict = Depends(require_auth)
):
    """Approve a documentation suggestion"""
    try:
        # Get feedback item and verify ownership
        feedback_result = supabase_service.supabase.table('doc_feedback').select(
            '*, repositories!inner(repo_name, owner, user_id)'
        ).eq('id', str(feedback_id)).execute()
        
        if not feedback_result.data:
            raise FeedbackNotFoundError(str(feedback_id))
        
        feedback_item = feedback_result.data[0]
        
        # Verify user owns the repository
        if feedback_item['repositories']['user_id'] != user['id']:
            raise FeedbackNotFoundError(str(feedback_id))
        
        repo = feedback_item['repositories']
        
        # Determine content to commit
        content_to_commit = request.approved_content or feedback_item['suggestion']
        commit_message = request.commit_message or f"docs: update {feedback_item['file_path']} based on user feedback"
        
        # Create GitHub commit if auto_commit is True
        github_commit = None
        if request.auto_commit and content_to_commit:
            try:
                commit_result = await github_service.create_commit(
                    owner=repo['owner'],
                    repo=repo['repo_name'],
                    file_path=feedback_item['file_path'],
                    content=content_to_commit,
                    message=commit_message
                )
                github_commit = commit_result
            except Exception as e:
                # Log error but don't fail the approval
                print(f"Failed to create GitHub commit: {e}")
        
        # Update feedback status
        update_data = {
            'status': 'approved',
            'updated_at': 'now()'
        }
        
        if request.approved_content:
            update_data['suggestion'] = request.approved_content
        
        supabase_service.supabase.table('doc_feedback').update(
            update_data
        ).eq('id', str(feedback_id)).execute()
        
        response_data = {
            "feedback_id": str(feedback_id),
            "status": "approved",
            "updated_at": feedback_item['updated_at']
        }
        
        if github_commit:
            response_data["github_commit"] = {
                "sha": github_commit.get('sha'),
                "url": github_commit.get('html_url'),
                "message": commit_message
            }
        
        return ApproveFeedbackResponse(
            data=response_data
        )
        
    except FeedbackNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve feedback: {str(e)}")


@router.post("/feedback/{feedback_id}/reject", response_model=RejectFeedbackResponse)
async def reject_feedback(
    feedback_id: UUID,
    request: RejectFeedbackRequest,
    user: dict = Depends(require_auth)
):
    """Reject a documentation suggestion"""
    try:
        # Get feedback item and verify ownership
        feedback_result = supabase_service.supabase.table('doc_feedback').select(
            '*, repositories!inner(user_id)'
        ).eq('id', str(feedback_id)).execute()
        
        if not feedback_result.data:
            raise FeedbackNotFoundError(str(feedback_id))
        
        feedback_item = feedback_result.data[0]
        
        # Verify user owns the repository
        if feedback_item['repositories']['user_id'] != user['id']:
            raise FeedbackNotFoundError(str(feedback_id))
        
        # Update feedback status
        update_data = {
            'status': 'rejected',
            'updated_at': 'now()',
            'rejection_reason': request.reason,
            'rejection_notes': request.notes
        }
        
        supabase_service.supabase.table('doc_feedback').update(
            update_data
        ).eq('id', str(feedback_id)).execute()
        
        return RejectFeedbackResponse(
            data={
                "feedback_id": str(feedback_id),
                "status": "rejected",
                "rejection_reason": request.reason,
                "updated_at": feedback_item['updated_at']
            }
        )
        
    except FeedbackNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reject feedback: {str(e)}")


@router.post("/feedback/{feedback_id}/regenerate")
async def regenerate_feedback_suggestion(
    feedback_id: UUID,
    user: dict = Depends(require_auth)
):
    """Regenerate suggestion for feedback item"""
    try:
        # Get feedback item and verify ownership
        feedback_result = supabase_service.supabase.table('doc_feedback').select(
            '*, repositories!inner(user_id, repo_name, owner)'
        ).eq('id', str(feedback_id)).execute()
        
        if not feedback_result.data:
            raise FeedbackNotFoundError(str(feedback_id))
        
        feedback_item = feedback_result.data[0]
        
        # Verify user owns the repository
        if feedback_item['repositories']['user_id'] != user['id']:
            raise FeedbackNotFoundError(str(feedback_id))
        
        repo = feedback_item['repositories']
        
        # Trigger feedback regeneration workflow
        workflow_id = await orkes_service.trigger_feedback_regeneration(
            feedback_id=str(feedback_id),
            repo_info={
                'name': repo['repo_name'],
                'owner': repo['owner']
            },
            feedback_data=feedback_item
        )
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": "Feedback suggestion regeneration triggered"
        }
        
    except FeedbackNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to regenerate feedback: {str(e)}")