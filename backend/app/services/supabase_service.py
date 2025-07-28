from supabase import create_client, Client
from typing import Optional, Dict, Any, List
import json

from app.core.config import settings


class SupabaseService:
    """Service for interacting with Supabase database"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            result = self.supabase.table('users').select('*').eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting user by ID: {e}")
            return None
    
    async def get_user_by_github_id(self, github_id: int) -> Optional[Dict[str, Any]]:
        """Get user by GitHub ID"""
        try:
            result = self.supabase.table('users').select('*').eq('github_id', github_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting user by GitHub ID: {e}")
            return None
    
    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new user"""
        try:
            result = self.supabase.table('users').insert(user_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user data"""
        try:
            result = self.supabase.table('users').update(update_data).eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating user: {e}")
            return None
    
    async def get_repository_by_id(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Get repository by ID"""
        try:
            result = self.supabase.table('repositories').select('*').eq('id', repo_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting repository: {e}")
            return None
    
    async def get_repositories_by_user(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get repositories for a user"""
        try:
            result = self.supabase.table('repositories').select('*').eq(
                'user_id', user_id
            ).range(offset, offset + limit - 1).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting user repositories: {e}")
            return []
    
    async def create_repository(self, repo_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new repository"""
        try:
            result = self.supabase.table('repositories').insert(repo_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating repository: {e}")
            return None
    
    async def update_repository(self, repo_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update repository data"""
        try:
            result = self.supabase.table('repositories').update(update_data).eq('id', repo_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating repository: {e}")
            return None
    
    async def delete_repository(self, repo_id: str) -> bool:
        """Delete repository"""
        try:
            self.supabase.table('repositories').delete().eq('id', repo_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting repository: {e}")
            return False
    
    async def get_feedback_by_id(self, feedback_id: str) -> Optional[Dict[str, Any]]:
        """Get feedback by ID"""
        try:
            result = self.supabase.table('doc_feedback').select('*').eq('id', feedback_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting feedback: {e}")
            return None
    
    async def create_feedback(self, feedback_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new feedback"""
        try:
            result = self.supabase.table('doc_feedback').insert(feedback_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating feedback: {e}")
            return None
    
    async def update_feedback(self, feedback_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update feedback data"""
        try:
            result = self.supabase.table('doc_feedback').update(update_data).eq('id', feedback_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating feedback: {e}")
            return None
    
    async def get_feedback_by_repo(self, repo_id: str, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get feedback for a repository"""
        try:
            query = self.supabase.table('doc_feedback').select('*').eq('repo_id', repo_id)
            
            if status:
                query = query.eq('status', status)
            
            result = query.range(offset, offset + limit - 1).order('created_at', desc=True).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting repository feedback: {e}")
            return []
    
    async def create_workflow_log(self, workflow_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create workflow log entry"""
        try:
            result = self.supabase.table('workflow_logs').insert(workflow_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error creating workflow log: {e}")
            return None
    
    async def update_workflow_log(self, workflow_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update workflow log"""
        try:
            result = self.supabase.table('workflow_logs').update(update_data).eq('id', workflow_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error updating workflow log: {e}")
            return None
    
    async def get_workflow_logs_by_repo(self, repo_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get workflow logs for a repository"""
        try:
            result = self.supabase.table('workflow_logs').select('*').eq(
                'repo_id', repo_id
            ).range(offset, offset + limit - 1).order('created_at', desc=True).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting workflow logs: {e}")
            return []
    
    async def get_analytics_data(self, user_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get analytics data for user's repositories"""
        try:
            # Get user's repositories
            repos_result = self.supabase.table('repositories').select('id').eq('user_id', user_id).execute()
            repo_ids = [repo['id'] for repo in repos_result.data or []]
            
            if not repo_ids:
                return {
                    'workflows': [],
                    'feedback': [],
                    'repositories': []
                }
            
            # Get workflows
            workflows_result = self.supabase.table('workflow_logs').select('*').in_(
                'repo_id', repo_ids
            ).gte('created_at', start_date).lte('created_at', end_date).execute()
            
            # Get feedback
            feedback_result = self.supabase.table('doc_feedback').select('*').in_(
                'repo_id', repo_ids
            ).gte('created_at', start_date).lte('created_at', end_date).execute()
            
            return {
                'workflows': workflows_result.data or [],
                'feedback': feedback_result.data or [],
                'repositories': repos_result.data or []
            }
            
        except Exception as e:
            print(f"Error getting analytics data: {e}")
            return {
                'workflows': [],
                'feedback': [],
                'repositories': []
            }
    
    async def search_repositories(self, user_id: str, search_term: str) -> List[Dict[str, Any]]:
        """Search user's repositories"""
        try:
            result = self.supabase.table('repositories').select('*').eq(
                'user_id', user_id
            ).ilike('repo_name', f'%{search_term}%').execute()
            return result.data or []
        except Exception as e:
            print(f"Error searching repositories: {e}")
            return []
    
    async def get_user_subscription_usage(self, user_id: str) -> Dict[str, int]:
        """Get user's current subscription usage"""
        try:
            # Count repositories
            repos_result = self.supabase.table('repositories').select(
                'id', count='exact'
            ).eq('user_id', user_id).execute()
            
            repo_count = repos_result.count or 0
            
            # Count workflows this month
            workflows_result = self.supabase.table('workflow_logs').select(
                'id', count='exact'
            ).eq('repo_id.in', f"(SELECT id FROM repositories WHERE user_id = '{user_id}')").\
            gte('created_at', 'date_trunc(\'month\', now())').execute()
            
            workflow_count = workflows_result.count or 0
            
            return {
                'repositories': repo_count,
                'workflows_this_month': workflow_count
            }
            
        except Exception as e:
            print(f"Error getting subscription usage: {e}")
            return {
                'repositories': 0,
                'workflows_this_month': 0
            }