from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.services.github_service import GitHubService


class CommentRequest(BaseModel):
    body: str

router = APIRouter()
github_service = GitHubService()


@router.get("/github/repository/{owner}/{repo_name}")
async def get_repository_info(owner: str, repo_name: str):
    """Get repository information from GitHub"""
    try:
        repo_info = await github_service.get_repository_info(owner, repo_name)
        if not repo_info:
            raise HTTPException(status_code=404, detail="Repository not found or not accessible")
        
        return {"data": repo_info}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get repository info: {str(e)}")


@router.get("/github/search/repositories")
async def search_repositories(
    query: str = Query(..., description="Search query"),
    user: Optional[str] = Query(None, description="Filter by user")
):
    """Search GitHub repositories"""
    try:
        results = await github_service.search_repositories(query, user)
        return {"data": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search repositories: {str(e)}")


@router.get("/github/repository/{owner}/{repo_name}/languages")
async def get_repository_languages(owner: str, repo_name: str):
    """Get programming languages used in repository"""
    try:
        languages = await github_service.get_repository_languages(owner, repo_name)
        return {"data": languages}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get repository languages: {str(e)}")


@router.get("/github/repository/{owner}/{repo_name}/file")
async def get_file_content(
    owner: str, 
    repo_name: str,
    path: str = Query(..., description="File path in repository"),
    ref: str = Query("main", description="Git reference (branch, tag, or commit)")
):
    """Get file content from repository"""
    try:
        file_content = await github_service.get_file_content(owner, repo_name, path, ref)
        if not file_content:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {"data": file_content}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file content: {str(e)}")


@router.get("/github/repository/{owner}/{repo_name}/pull/{pr_number}/files")
async def get_pull_request_files(owner: str, repo_name: str, pr_number: int):
    """Get files changed in a pull request"""
    try:
        files = await github_service.get_pull_request_files(owner, repo_name, pr_number)
        return {"data": files}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get PR files: {str(e)}")


@router.post("/github/repository/{owner}/{repo_name}/pull/{pr_number}/comment")
async def create_pull_request_comment(
    owner: str, 
    repo_name: str, 
    pr_number: int,
    request: CommentRequest
):
    """Create a comment on a pull request"""
    try:
        comment = await github_service.create_pull_request_comment(owner, repo_name, pr_number, request.body)
        if not comment:
            raise HTTPException(status_code=500, detail="Failed to create comment")
        
        return {"data": comment}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create PR comment: {str(e)}")


@router.get("/github/repository/{owner}/{repo_name}/commit/{commit_sha}/files")
async def get_commit_files(owner: str, repo_name: str, commit_sha: str):
    """Get files changed in a commit"""
    try:
        files = await github_service.get_commit_files(owner, repo_name, commit_sha)
        return {"data": files}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get commit files: {str(e)}")


@router.get("/github/repository/{owner}/{repo_name}/access")
async def check_repository_access(owner: str, repo_name: str):
    """Check if we have access to repository"""
    try:
        has_access = await github_service.check_user_repository_access(owner, repo_name)
        return {"data": {"has_access": has_access}}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check repository access: {str(e)}")