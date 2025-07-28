import os
import requests
from typing import Dict, List, Any, Optional
from github import Github
from decouple import config, Config, RepositoryEnv


class GitHubClient:
    """GitHub API client for fetching PR diffs and repository information."""
    
    def __init__(self, access_token: str = None):
        # Load config from backend/.env file
        backend_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        env_config = Config(RepositoryEnv(backend_env_path)) if os.path.exists(backend_env_path) else config
        
        self.access_token = access_token or env_config('GITHUB_TOKEN', default='')
        self.github = Github(self.access_token) if self.access_token else None
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.access_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DocuSync-Agent"
        }
    
    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> Optional[str]:
        """
        Fetch the diff for a specific pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            String containing the PR diff or None if failed
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            return response.text
        except Exception as e:
            print(f"Error fetching PR diff: {e}")
            return None
    
    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get list of files changed in a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            List of file change objects
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error fetching PR files: {e}")
            return []
    
    def get_pr_details(self, owner: str, repo: str, pr_number: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            PR details dictionary or None if failed
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error fetching PR details: {e}")
            return None
    
    def get_commits_in_pr(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get all commits in a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            List of commit objects
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/commits"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"Error fetching PR commits: {e}")
            return []
    
    def analyze_pr_changes(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """
        Comprehensive analysis of PR changes including diff, files, and metadata.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            Dictionary containing complete PR analysis
        """
        pr_details = self.get_pr_details(owner, repo, pr_number)
        if not pr_details:
            return {"error": "Could not fetch PR details"}
        
        diff = self.get_pr_diff(owner, repo, pr_number)
        files = self.get_pr_files(owner, repo, pr_number)
        commits = self.get_commits_in_pr(owner, repo, pr_number)
        
        # Analyze file types and changes
        file_analysis = self._analyze_file_changes(files)
        
        return {
            "pr_details": {
                "title": pr_details.get("title"),
                "body": pr_details.get("body"),
                "state": pr_details.get("state"),
                "created_at": pr_details.get("created_at"),
                "updated_at": pr_details.get("updated_at"),
                "author": pr_details.get("user", {}).get("login"),
                "base_branch": pr_details.get("base", {}).get("ref"),
                "head_branch": pr_details.get("head", {}).get("ref"),
                "additions": pr_details.get("additions", 0),
                "deletions": pr_details.get("deletions", 0),
                "changed_files": pr_details.get("changed_files", 0)
            },
            "diff": diff,
            "files": files,
            "commits": commits,
            "file_analysis": file_analysis,
            "documentation_impact": self._assess_documentation_impact(files, diff)
        }
    
    def _analyze_file_changes(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the types of files changed and their impact."""
        analysis = {
            "total_files": len(files),
            "file_types": {},
            "documentation_files": [],
            "code_files": [],
            "config_files": [],
            "test_files": []
        }
        
        for file in files:
            filename = file.get("filename", "")
            status = file.get("status", "")
            
            # Categorize files
            if filename.endswith(('.md', '.rst', '.txt', '.adoc')):
                analysis["documentation_files"].append(filename)
            elif filename.endswith(('.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c')):
                analysis["code_files"].append(filename)
            elif filename.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.cfg')):
                analysis["config_files"].append(filename)
            elif 'test' in filename.lower() or filename.endswith(('.test.js', '.test.py', '_test.py')):
                analysis["test_files"].append(filename)
            
            # Track file extensions
            ext = filename.split('.')[-1] if '.' in filename else 'no_extension'
            analysis["file_types"][ext] = analysis["file_types"].get(ext, 0) + 1
        
        return analysis
    
    def _assess_documentation_impact(self, files: List[Dict[str, Any]], diff: str) -> Dict[str, Any]:
        """Assess the potential impact on documentation."""
        impact = {
            "requires_doc_update": False,
            "impact_level": "low",
            "reasons": [],
            "suggested_actions": []
        }
        
        # Check for API changes
        if diff and any(keyword in diff.lower() for keyword in 
                       ['def ', 'function ', 'class ', 'interface ', 'endpoint', 'route']):
            impact["requires_doc_update"] = True
            impact["impact_level"] = "high"
            impact["reasons"].append("API or function definitions changed")
            impact["suggested_actions"].append("Update API documentation")
        
        # Check for configuration changes
        config_changed = any(f.get("filename", "").endswith(('.json', '.yaml', '.yml', '.toml')) 
                           for f in files)
        if config_changed:
            impact["requires_doc_update"] = True
            impact["impact_level"] = "medium"
            impact["reasons"].append("Configuration files modified")
            impact["suggested_actions"].append("Update configuration documentation")
        
        # Check for README or documentation changes
        readme_changed = any('readme' in f.get("filename", "").lower() for f in files)
        if readme_changed:
            impact["impact_level"] = "medium"
            impact["reasons"].append("README or documentation files directly modified")
        
        return impact
    
    def get_file_content(self, owner: str, repo: str, file_path: str, ref: str = None) -> Optional[Dict[str, Any]]:
        """
        Get the content of a file from the repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            file_path: Path to the file (e.g., 'README.md')
            ref: Branch/commit reference (optional, defaults to default branch)
            
        Returns:
            Dictionary with file content and metadata or None if failed
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}"
            params = {}
            if ref:
                params['ref'] = ref
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            file_data = response.json()
            
            # Decode base64 content
            import base64
            content = base64.b64decode(file_data['content']).decode('utf-8')
            
            return {
                'content': content,
                'sha': file_data['sha'],
                'path': file_data['path'],
                'name': file_data['name'],
                'size': file_data['size'],
                'download_url': file_data.get('download_url'),
                'encoding': file_data.get('encoding', 'base64')
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"File not found: {file_path}")
                return None
            print(f"HTTP error getting file content: {e}")
            return None
        except Exception as e:
            print(f"Error getting file content: {e}")
            return None
    
    def update_file_content(self, owner: str, repo: str, file_path: str, new_content: str, 
                          commit_message: str, branch: str, current_sha: str = None) -> bool:
        """
        Update the content of a file in the repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            file_path: Path to the file (e.g., 'README.md')
            new_content: New file content
            commit_message: Commit message for the update
            branch: Branch to update
            current_sha: Current SHA of the file (required for updates)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import base64
            
            # If no SHA provided, get current file to get SHA
            if not current_sha:
                current_file = self.get_file_content(owner, repo, file_path, branch)
                if not current_file:
                    print(f"Could not get current file content for SHA: {file_path}")
                    return False
                current_sha = current_file['sha']
            
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}"
            
            # Encode content to base64
            encoded_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
            
            data = {
                'message': commit_message,
                'content': encoded_content,
                'sha': current_sha,
                'branch': branch
            }
            
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ File updated successfully: {file_path}")
            print(f"   Commit SHA: {result['commit']['sha']}")
            print(f"   Branch: {branch}")
            
            return True
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP error updating file: {e}")
            if e.response:
                print(f"   Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"❌ Error updating file: {e}")
            return False
    
    def create_file_content(self, owner: str, repo: str, file_path: str, content: str,
                          commit_message: str, branch: str) -> bool:
        """
        Create a new file in the repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            file_path: Path for the new file
            content: File content
            commit_message: Commit message
            branch: Branch to create file on
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import base64
            
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{file_path}"
            
            # Encode content to base64
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            data = {
                'message': commit_message,
                'content': encoded_content,
                'branch': branch
            }
            
            response = requests.put(url, headers=self.headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            print(f"✅ File created successfully: {file_path}")
            print(f"   Commit SHA: {result['commit']['sha']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating file: {e}")
            return False