from github import Github, GithubException, Auth
from typing import Optional, Dict, Any, List
import base64
import httpx
from datetime import datetime
import jwt
import time

from app.core.config import settings


class GitHubService:
    """Service for interacting with GitHub API"""
    
    def __init__(self):
        # Use GitHub App authentication if available, otherwise fallback to token
        self.github = self._create_github_client()
        self.webhook_secret = settings.github_webhook_secret
        self.app_id = settings.github_app_id
    
    def _create_github_client(self) -> Optional[Github]:
        """Create GitHub client with appropriate authentication"""
        try:
            # Try personal access token first (simpler and more reliable for testing)
            if settings.github_token:
                print(f"Using GitHub personal access token authentication")
                return Github(settings.github_token)
            
            # Fallback to GitHub App authentication
            if hasattr(settings, 'github_app_id') and hasattr(settings, 'github_private_key'):
                try:
                    print(f"Trying GitHub App authentication")
                    # Create JWT for GitHub App authentication
                    private_key = settings.github_private_key_decoded
                    auth = Auth.AppAuth(settings.github_app_id, private_key)
                    return Github(auth=auth)
                except Exception as e:
                    print(f"GitHub App authentication failed: {e}")
            
            print("No GitHub authentication configured")
            return None
            
        except Exception as e:
            print(f"Error creating GitHub client: {e}")
            return None
    
    def _get_installation_client(self, installation_id: int) -> Optional[Github]:
        """Get GitHub client for a specific app installation"""
        try:
            if not self.github:
                return None
            
            # Get installation access token
            installation = self.github.get_app().get_installation(installation_id)
            auth = Auth.AppInstallationAuth(
                settings.github_app_id,
                settings.github_private_key_decoded,
                installation_id
            )
            return Github(auth=auth)
            
        except Exception as e:
            print(f"Error getting installation client: {e}")
            return None
    
    async def get_repository_info(self, owner: str, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get repository information from GitHub"""
        try:
            if not self.github:
                return None
            
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            
            return {
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "owner": repo.owner.login,
                "description": repo.description,
                "private": repo.private,
                "default_branch": repo.default_branch,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url,
                "html_url": repo.html_url,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                "language": repo.language,
                "languages": dict(repo.get_languages()) if hasattr(repo, 'get_languages') else {},
                "topics": repo.get_topics() if hasattr(repo, 'get_topics') else [],
                "has_wiki": repo.has_wiki,
                "has_pages": repo.has_pages,
                "has_issues": repo.has_issues
            }
            
        except GithubException as e:
            print(f"GitHub API error getting repository info: {e}")
            return None
        except Exception as e:
            print(f"Error getting repository info: {e}")
            return None
    
    async def install_webhook(self, owner: str, repo_name: str) -> bool:
        """Install DocuSync webhook on repository"""
        try:
            if not self.github:
                return False
            
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            
            # Check if webhook already exists
            existing_webhooks = repo.get_hooks()
            webhook_url = f"{settings.supabase_url}/webhooks/github"  # Adjust based on deployment
            
            for hook in existing_webhooks:
                if hook.config.get('url') == webhook_url:
                    print(f"Webhook already exists for {owner}/{repo_name}")
                    return True
            
            # Create new webhook
            config = {
                "url": webhook_url,
                "content_type": "json",
                "secret": self.webhook_secret,
                "insecure_ssl": "0"
            }
            
            events = [
                "push",
                "pull_request",
                "issues",
                "pull_request_review"
            ]
            
            repo.create_hook(
                name="web",
                config=config,
                events=events,
                active=True
            )
            
            print(f"Webhook installed for {owner}/{repo_name}")
            return True
            
        except GithubException as e:
            print(f"GitHub API error installing webhook: {e}")
            return False
        except Exception as e:
            print(f"Error installing webhook: {e}")
            return False
    
    async def remove_webhook(self, owner: str, repo_name: str) -> bool:
        """Remove DocuSync webhook from repository"""
        try:
            if not self.github:
                return False
            
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            webhook_url = f"{settings.supabase_url}/webhooks/github"
            
            # Find and delete webhook
            hooks = repo.get_hooks()
            for hook in hooks:
                if hook.config.get('url') == webhook_url:
                    hook.delete()
                    print(f"Webhook removed from {owner}/{repo_name}")
                    return True
            
            print(f"No DocuSync webhook found for {owner}/{repo_name}")
            return True
            
        except GithubException as e:
            print(f"GitHub API error removing webhook: {e}")
            return False
        except Exception as e:
            print(f"Error removing webhook: {e}")
            return False
    
    async def get_file_content(self, owner: str, repo_name: str, file_path: str, ref: str = "main") -> Optional[Dict[str, Any]]:
        """Get file content from repository"""
        try:
            if not self.github:
                return None
            
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            
            try:
                content_file = repo.get_contents(file_path, ref=ref)
            except GithubException as e:
                if e.status == 404:
                    return None
                raise
            
            # Decode content if it's a file
            if content_file.type == "file":
                content = base64.b64decode(content_file.content).decode('utf-8')
                return {
                    "content": content,
                    "sha": content_file.sha,
                    "size": content_file.size,
                    "encoding": content_file.encoding,
                    "path": content_file.path,
                    "type": content_file.type
                }
            
            return None
            
        except GithubException as e:
            print(f"GitHub API error getting file content: {e}")
            return None
        except Exception as e:
            print(f"Error getting file content: {e}")
            return None
    
    async def create_commit(self, owner: str, repo_name: str, file_path: str, content: str, message: str, branch: str = "main") -> Optional[Dict[str, Any]]:
        """Create a commit with file changes"""
        try:
            if not self.github:
                return None
            
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            
            # Check if file exists
            try:
                existing_file = repo.get_contents(file_path, ref=branch)
                # Update existing file
                commit = repo.update_file(
                    path=file_path,
                    message=message,
                    content=content,
                    sha=existing_file.sha,
                    branch=branch
                )
            except GithubException as e:
                if e.status == 404:
                    # Create new file
                    commit = repo.create_file(
                        path=file_path,
                        message=message,
                        content=content,
                        branch=branch
                    )
                else:
                    raise
            
            return {
                "sha": commit["commit"].sha,
                "html_url": commit["commit"].html_url,
                "message": commit["commit"].message,
                "author": commit["commit"].author.name if commit["commit"].author else None,
                "date": commit["commit"].author.date.isoformat() if commit["commit"].author else None
            }
            
        except GithubException as e:
            print(f"GitHub API error creating commit: {e}")
            return None
        except Exception as e:
            print(f"Error creating commit: {e}")
            return None
    
    async def create_pull_request_comment(self, owner: str, repo_name: str, pr_number: int, body: str) -> Optional[Dict[str, Any]]:
        """Create a comment on a pull request"""
        try:
            if not self.github:
                return None
            
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            
            comment = pr.create_issue_comment(body)
            
            return {
                "id": comment.id,
                "html_url": comment.html_url,
                "body": comment.body,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
                "user": comment.user.login if comment.user else None
            }
            
        except GithubException as e:
            print(f"GitHub API error creating PR comment: {e}")
            return None
        except Exception as e:
            print(f"Error creating PR comment: {e}")
            return None
    
    async def get_pull_request_files(self, owner: str, repo_name: str, pr_number: int) -> List[Dict[str, Any]]:
        """Get files changed in a pull request"""
        try:
            if not self.github:
                return []
            
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            pr = repo.get_pull(pr_number)
            
            files = []
            for file in pr.get_files():
                files.append({
                    "filename": file.filename,
                    "status": file.status,  # added, removed, modified
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "patch": file.patch,
                    "sha": file.sha,
                    "blob_url": file.blob_url,
                    "raw_url": file.raw_url
                })
            
            return files
            
        except GithubException as e:
            print(f"GitHub API error getting PR files: {e}")
            return []
        except Exception as e:
            print(f"Error getting PR files: {e}")
            return []
    
    async def get_commit_files(self, owner: str, repo_name: str, commit_sha: str) -> List[Dict[str, Any]]:
        """Get files changed in a commit"""
        try:
            if not self.github:
                return []
            
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            commit = repo.get_commit(commit_sha)
            
            files = []
            for file in commit.files:
                files.append({
                    "filename": file.filename,
                    "status": file.status,
                    "additions": file.additions,
                    "deletions": file.deletions,
                    "changes": file.changes,
                    "patch": file.patch,
                    "sha": file.sha,
                    "blob_url": file.blob_url,
                    "raw_url": file.raw_url
                })
            
            return files
            
        except GithubException as e:
            print(f"GitHub API error getting commit files: {e}")
            return []
        except Exception as e:
            print(f"Error getting commit files: {e}")
            return []
    
    async def search_repositories(self, query: str, user: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search GitHub repositories"""
        try:
            if not self.github:
                return []
            
            search_query = query
            if user:
                search_query = f"{query} user:{user}"
            
            repositories = self.github.search_repositories(search_query)
            
            results = []
            for repo in repositories[:50]:  # Limit to 50 results
                results.append({
                    "id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "owner": repo.owner.login,
                    "description": repo.description,
                    "private": repo.private,
                    "html_url": repo.html_url,
                    "language": repo.language,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
                })
            
            return results
            
        except GithubException as e:
            print(f"GitHub API error searching repositories: {e}")
            return []
        except Exception as e:
            print(f"Error searching repositories: {e}")
            return []
    
    async def check_user_repository_access(self, owner: str, repo_name: str) -> bool:
        """Check if the authenticated user has access to repository"""
        try:
            if not self.github:
                return False
            
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            
            # Try to access repository (this will raise exception if no access)
            _ = repo.name
            return True
            
        except GithubException as e:
            if e.status == 404:
                return False
            print(f"GitHub API error checking repository access: {e}")
            return False
        except Exception as e:
            print(f"Error checking repository access: {e}")
            return False
    
    async def get_repository_languages(self, owner: str, repo_name: str) -> Dict[str, int]:
        """Get programming languages used in repository"""
        try:
            if not self.github:
                return {}
            
            repo = self.github.get_repo(f"{owner}/{repo_name}")
            return dict(repo.get_languages())
            
        except GithubException as e:
            print(f"GitHub API error getting repository languages: {e}")
            return {}
        except Exception as e:
            print(f"Error getting repository languages: {e}")
            return {}