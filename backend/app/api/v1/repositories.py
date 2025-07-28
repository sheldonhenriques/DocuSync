from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from uuid import UUID
import re
from urllib.parse import urlparse

from app.middleware.auth import require_auth
from app.models.repository import (
    Repository, CreateRepositoryRequest, CreateRepositoryResponse,
    UpdateRepositoryConfigRequest, UpdateRepositoryConfigResponse,
    RepositoryListResponse, RepositoryResponse, DocConfig
)
from app.models.base import PaginationParams, PaginationResponse
from app.middleware.error_handler import RepositoryNotFoundError, ValidationError
from app.services.supabase_service import SupabaseService
from app.services.github_service import GitHubService
from app.services.orkes_service import OrkesService

router = APIRouter()

supabase_service = SupabaseService()
github_service = GitHubService()
orkes_service = OrkesService()


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse GitHub URL to extract owner and repo name"""
    # Support various GitHub URL formats
    patterns = [
        r"github\.com/([^/]+)/([^/]+)/?$",
        r"github\.com/([^/]+)/([^/]+)\.git$",
        r"github\.com/([^/]+)/([^/]+)/.*$"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            owner, repo = match.groups()
            # Remove .git suffix if present
            repo = repo.replace('.git', '')
            return owner, repo
    
    raise ValidationError("Invalid GitHub URL format")


@router.get("/repositories", response_model=RepositoryListResponse)
async def get_repositories(
    pagination: PaginationParams = Depends(),
    user: dict = Depends(require_auth)
):
    """Get all repositories for authenticated user"""
    try:
        # Calculate offset for pagination
        offset = (pagination.page - 1) * pagination.per_page
        
        # Get repositories from database
        result = supabase_service.supabase.table('repositories').select(
            '*', count='exact'
        ).eq(
            'user_id', user['id']
        ).range(
            offset, offset + pagination.per_page - 1
        ).order('created_at', desc=True).execute()
        
        repositories = [Repository(**repo) for repo in result.data]
        total_count = result.count or 0
        total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
        
        pagination_response = PaginationResponse(
            page=pagination.page,
            per_page=pagination.per_page,
            total=total_count,
            total_pages=total_pages
        )
        
        return RepositoryListResponse(
            data=repositories,
            pagination=pagination_response
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repositories: {str(e)}")


@router.get("/repositories/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: UUID,
    user: dict = Depends(require_auth)
):
    """Get specific repository by ID"""
    try:
        result = supabase_service.supabase.table('repositories').select(
            '*'
        ).eq('id', str(repo_id)).eq('user_id', user['id']).execute()
        
        if not result.data:
            raise RepositoryNotFoundError(str(repo_id))
        
        repository = Repository(**result.data[0])
        return RepositoryResponse(data=repository)
        
    except RepositoryNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repository: {str(e)}")


@router.post("/repositories", response_model=CreateRepositoryResponse)
async def create_repository(
    request: CreateRepositoryRequest,
    user: dict = Depends(require_auth)
):
    """Add new repository to DocuSync monitoring"""
    try:
        # Parse GitHub URL
        owner, repo_name = parse_github_url(request.github_repo_url)
        full_name = f"{owner}/{repo_name}"
        
        # Validate repository exists and user has access
        repo_info = await github_service.get_repository_info(owner, repo_name)
        if not repo_info:
            raise ValidationError("Repository not found or not accessible")
        
        # Check if repository is already monitored by this user
        existing = supabase_service.supabase.table('repositories').select(
            'id'
        ).eq('user_id', user['id']).eq('full_name', full_name).execute()
        
        if existing.data:
            raise ValidationError("Repository is already being monitored")
        
        # Set default config if not provided
        doc_config = request.doc_config or DocConfig()
        
        # Create repository record
        repo_data = {
            'user_id': user['id'],
            'github_repo_id': repo_info['id'],
            'repo_name': repo_name,
            'owner': owner,
            'full_name': full_name,
            'doc_config': doc_config.dict(),
            'status': 'active'
        }
        
        result = supabase_service.supabase.table('repositories').insert(
            repo_data
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create repository")
        
        created_repo = result.data[0]
        
        # Install GitHub webhook
        webhook_installed = await github_service.install_webhook(owner, repo_name)
        
        # Trigger initial scan workflow
        workflow_id = await orkes_service.trigger_initial_scan(
            repo_id=created_repo['id'],
            repo_info=repo_info
        )
        
        return CreateRepositoryResponse(
            data={
                "id": created_repo['id'],
                "repo_name": full_name,
                "status": "active",
                "webhook_installed": webhook_installed,
                "initial_scan_triggered": bool(workflow_id)
            },
            message="Repository added successfully. Initial documentation scan started."
        )
        
    except ValidationError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create repository: {str(e)}")


@router.put("/repositories/{repo_id}/config", response_model=UpdateRepositoryConfigResponse)
async def update_repository_config(
    repo_id: UUID,
    request: UpdateRepositoryConfigRequest,
    user: dict = Depends(require_auth)
):
    """Update repository configuration"""
    try:
        # Verify repository exists and belongs to user
        existing = supabase_service.supabase.table('repositories').select(
            '*'
        ).eq('id', str(repo_id)).eq('user_id', user['id']).execute()
        
        if not existing.data:
            raise RepositoryNotFoundError(str(repo_id))
        
        # Update repository configuration
        result = supabase_service.supabase.table('repositories').update({
            'doc_config': request.doc_config.dict(),
            'updated_at': 'now()'
        }).eq('id', str(repo_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to update repository")
        
        updated_repo = Repository(**result.data[0])
        
        return UpdateRepositoryConfigResponse(
            data=updated_repo
        )
        
    except RepositoryNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update repository: {str(e)}")


@router.delete("/repositories/{repo_id}")
async def delete_repository(
    repo_id: UUID,
    user: dict = Depends(require_auth)
):
    """Remove repository from DocuSync monitoring"""
    try:
        # Verify repository exists and belongs to user
        existing = supabase_service.supabase.table('repositories').select(
            'owner', 'repo_name'
        ).eq('id', str(repo_id)).eq('user_id', user['id']).execute()
        
        if not existing.data:
            raise RepositoryNotFoundError(str(repo_id))
        
        repo = existing.data[0]
        
        # Remove GitHub webhook
        await github_service.remove_webhook(repo['owner'], repo['repo_name'])
        
        # Delete repository record
        supabase_service.supabase.table('repositories').delete().eq(
            'id', str(repo_id)
        ).execute()
        
        return {"success": True, "message": "Repository removed successfully"}
        
    except RepositoryNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete repository: {str(e)}")


@router.post("/repositories/{repo_id}/sync")
async def trigger_repository_sync(
    repo_id: UUID,
    user: dict = Depends(require_auth)
):
    """Manually trigger documentation sync for repository"""
    try:
        # Verify repository exists and belongs to user
        existing = supabase_service.supabase.table('repositories').select(
            '*'
        ).eq('id', str(repo_id)).eq('user_id', user['id']).execute()
        
        if not existing.data:
            raise RepositoryNotFoundError(str(repo_id))
        
        repo = existing.data[0]
        
        # Trigger manual sync workflow
        workflow_id = await orkes_service.trigger_manual_sync(
            repo_id=str(repo_id),
            repo_info={
                'owner': repo['owner'],
                'name': repo['repo_name'],
                'full_name': repo['full_name']
            }
        )
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": "Documentation sync triggered successfully"
        }
        
    except RepositoryNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to trigger sync: {str(e)}")