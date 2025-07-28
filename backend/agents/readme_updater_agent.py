import os
import json
import logging
from typing import Dict, Any
from conductor.client.worker.worker_task import worker_task
from conductor.client.configuration.configuration import Configuration
from conductor.client.configuration.settings.authentication_settings import AuthenticationSettings
from conductor.client.automator.task_handler import TaskHandler
from decouple import Config, RepositoryEnv
from datetime import datetime

from github_client import GitHubClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReadmeUpdaterAgent:
    """
    README Updater Agent that updates README.md files on PR branches
    with AI-generated documentation insights instead of posting comments.
    """
    
    def __init__(self, github_token: str = None, conductor_server_url: str = None, conductor_key: str = None):
        # Load config from backend/.env file
        backend_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        if os.path.exists(backend_env_path):
            env_config = Config(RepositoryEnv(backend_env_path))
        else:
            from decouple import config as env_config
        
        # Use provided values or fall back to .env file
        self.github_token = github_token or env_config('GITHUB_TOKEN', default='')
        conductor_server_url = conductor_server_url or env_config('ORKES_SERVER_URL', default='http://localhost:8080/api')
        conductor_key = conductor_key or env_config('ORKES_API_KEY', default='')
        
        self.github_client = GitHubClient(self.github_token)
        
        # Configure Conductor client
        if conductor_key:
            # For Orkes Cloud, the API key is used as both key_id and key_secret
            auth_settings = AuthenticationSettings(key_id=conductor_key, key_secret=conductor_key)
            configuration = Configuration(
                server_api_url=conductor_server_url,
                authentication_settings=auth_settings
            )
        else:
            # Default configuration for local/development
            configuration = Configuration(server_api_url=conductor_server_url)
        
        self.task_handler = TaskHandler(configuration=configuration)
        
        # Register worker tasks
        self.register_tasks()
    
    def register_tasks(self):
        """Register all worker tasks with Conductor."""
        logger.info("Registering README Updater Agent tasks...")
        # Tasks are automatically registered via @worker_task decorator
    
    def start_polling(self):
        """Start polling for tasks from Conductor."""
        logger.info("Starting README Updater Agent polling...")
        self.task_handler.start_processes()
    
    @worker_task(task_definition_name='update_readme_with_ai_insights')
    def update_readme_with_ai_insights(self, pr_analysis: Dict[str, Any], ai_summary: Dict[str, Any] = None, 
                                     ai_comment: Dict[str, Any] = None, documentation_suggestions: Dict[str, Any] = None,
                                     webhook_payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Update the README.md file on the PR branch with AI-generated documentation insights.
        
        Args:
            pr_analysis: Analysis results from the commit watcher
            ai_summary: AI-generated summary from Gemini (optional)
            ai_comment: AI-generated insights from Gemini (preferred)
            documentation_suggestions: AI-generated documentation suggestions (optional)
            webhook_payload: Original GitHub webhook payload (optional)
            
        Returns:
            Result of the README update operation
        """
        try:
            logger.info(f"Updating README.md for PR #{pr_analysis.get('pr_number', 'unknown')}")
            
            # Extract PR information
            repo_full_name = pr_analysis.get('repository', '')
            pr_number = pr_analysis.get('pr_number')
            
            if not repo_full_name or not pr_number:
                return {"error": "Missing repository or PR number information"}
            
            # Split repository name
            try:
                owner, repo = repo_full_name.split('/')
            except ValueError:
                return {"error": f"Invalid repository format: {repo_full_name}"}
            
            # Get PR branch information from webhook or API
            pr_branch = self._get_pr_branch(webhook_payload, owner, repo, pr_number)
            if not pr_branch:
                return {"error": "Could not determine PR branch"}
            
            logger.info(f"Updating README.md on branch: {pr_branch}")
            
            # Get current README.md content
            current_readme = self.github_client.get_file_content(owner, repo, 'README.md', pr_branch)
            if not current_readme:
                logger.warning("README.md not found, will create new one")
                current_content = "# " + repo + "\n\n"
                current_sha = None
            else:
                current_content = current_readme['content']
                current_sha = current_readme['sha']
            
            # Generate enhanced README content
            enhanced_content = self._generate_enhanced_readme(
                current_content=current_content,
                pr_analysis=pr_analysis,
                ai_summary=ai_summary,
                ai_comment=ai_comment,
                documentation_suggestions=documentation_suggestions
            )
            
            # Create commit message
            commit_message = f"📚 AI-Enhanced Documentation Update\n\nAutomatically updated README.md with AI-generated insights for PR #{pr_number}.\n\n🤖 Generated by DocuSync AI"
            
            # Update or create the README file
            if current_readme:
                success = self.github_client.update_file_content(
                    owner=owner,
                    repo=repo,
                    file_path='README.md',
                    new_content=enhanced_content,
                    commit_message=commit_message,
                    branch=pr_branch,
                    current_sha=current_sha
                )
            else:
                success = self.github_client.create_file_content(
                    owner=owner,
                    repo=repo,
                    file_path='README.md',
                    content=enhanced_content,
                    commit_message=commit_message,
                    branch=pr_branch
                )
            
            if success:
                logger.info(f"✅ README.md updated successfully on branch {pr_branch}")
                return {
                    "status": "success",
                    "message": f"README.md updated on branch {pr_branch}",
                    "repository": repo_full_name,
                    "branch": pr_branch,
                    "file": "README.md",
                    "pr_number": pr_number
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to update README.md file"
                }
                
        except Exception as e:
            logger.error(f"Error updating README.md: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _get_pr_branch(self, webhook_payload: Dict[str, Any], owner: str, repo: str, pr_number: int) -> str:
        """Get the PR branch name from webhook or API."""
        
        # Try to get from webhook payload first
        if webhook_payload and 'pull_request' in webhook_payload:
            head_ref = webhook_payload['pull_request'].get('head', {}).get('ref')
            if head_ref:
                return head_ref
        
        # Fall back to API call
        try:
            pr_details = self.github_client.get_pr_details(owner, repo, pr_number)
            if pr_details:
                return pr_details.get('head', {}).get('ref')
        except Exception as e:
            logger.error(f"Error getting PR branch from API: {e}")
        
        return None
    
    def _generate_enhanced_readme(self, current_content: str, pr_analysis: Dict[str, Any],
                                ai_summary: Dict[str, Any] = None, ai_comment: Dict[str, Any] = None,
                                documentation_suggestions: Dict[str, Any] = None) -> str:
        """Generate enhanced README content with AI insights."""
        
        # Extract AI insights
        ai_insights = ""
        if ai_comment:
            ai_insights = self._extract_llm_output(ai_comment)
        elif ai_summary:
            ai_insights = self._extract_llm_output(ai_summary)
        
        # Create documentation update section
        timestamp = datetime.now().strftime("%Y-%m-%d")
        pr_number = pr_analysis.get('pr_number', 'unknown')
        
        documentation_section = f"""

## 📚 Recent Documentation Updates

### PR #{pr_number} - AI-Enhanced Documentation ({timestamp})

{ai_insights if ai_insights else self._generate_default_insights(pr_analysis)}

---
*🤖 This documentation update was automatically generated by DocuSync AI*

"""
        
        # Find where to insert the documentation section
        enhanced_content = self._insert_documentation_section(current_content, documentation_section)
        
        return enhanced_content
    
    def _insert_documentation_section(self, current_content: str, documentation_section: str) -> str:
        """Insert the documentation section into the README at an appropriate location."""
        
        lines = current_content.split('\n')
        
        # Look for existing "Recent Documentation Updates" section to replace
        start_idx = None
        end_idx = None
        
        for i, line in enumerate(lines):
            if "Recent Documentation Updates" in line or "📚 Recent Documentation Updates" in line:
                start_idx = i - 1 if i > 0 and lines[i - 1].strip() == "" else i
                # Find the end of this section (next ## heading or end of file)
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith('## ') and j > i + 1:
                        end_idx = j
                        break
                    elif lines[j].strip() == "*🤖 This documentation update was automatically generated by DocuSync AI*":
                        end_idx = j + 1
                        break
                if end_idx is None:
                    end_idx = len(lines)
                break
        
        if start_idx is not None and end_idx is not None:
            # Replace existing section
            new_lines = lines[:start_idx] + documentation_section.split('\n') + lines[end_idx:]
        else:
            # Insert after the first heading, or at the end if no headings
            insert_idx = len(lines)
            for i, line in enumerate(lines):
                if line.startswith('# ') and i > 0:  # Skip the very first heading
                    # Insert after this heading and any immediate content
                    for j in range(i + 1, len(lines)):
                        if lines[j].startswith('#') or j == len(lines) - 1:
                            insert_idx = j
                            break
                    break
                elif line.startswith('## ') and i > 2:  # Insert before first ## heading
                    insert_idx = i
                    break
            
            new_lines = lines[:insert_idx] + documentation_section.split('\n') + lines[insert_idx:]
        
        return '\n'.join(new_lines)
    
    def _generate_default_insights(self, pr_analysis: Dict[str, Any]) -> str:
        """Generate default insights when AI content is not available."""
        
        priority = pr_analysis.get('priority', 'unknown')
        requires_docs = pr_analysis.get('requires_documentation', False)
        files_changed = pr_analysis.get('changes_summary', {}).get('files_changed', 0)
        
        insights = f"""#### 🔍 Change Analysis
- **Files Modified**: {files_changed}
- **Priority**: {priority.title()}
- **Documentation Impact**: {'High' if requires_docs else 'Low'}

#### 📊 Summary
This PR introduces changes that {'require' if requires_docs else 'do not require'} significant documentation updates. 

#### 🎯 Key Changes
{chr(10).join(f"- {action}" for action in pr_analysis.get('suggested_actions', ['Code improvements and maintenance']))}

#### ✨ Status
The documentation has been automatically analyzed and updated with relevant insights."""
        
        return insights
    
    def _extract_llm_output(self, llm_result: Dict[str, Any]) -> str:
        """Extract the generated text from LLM task output."""
        if not llm_result:
            return None
            
        # Handle different LLM response formats
        if isinstance(llm_result, str):
            return llm_result
        
        if isinstance(llm_result, dict):
            # Try different possible keys
            possible_keys = ['output', 'result', 'text', 'response', 'generated_text', 'content']
            
            for key in possible_keys:
                if key in llm_result and llm_result[key]:
                    value = llm_result[key]
                    if isinstance(value, dict):
                        # Try to extract from nested dict
                        for nested_key in ['text', 'content', 'message', 'output']:
                            if nested_key in value and value[nested_key]:
                                return str(value[nested_key])
                        return str(value)
                    return str(value)
        
        return str(llm_result) if llm_result else None


# Main execution for running the agent
if __name__ == "__main__":
    # Load config from backend/.env file
    backend_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(backend_env_path):
        env_config = Config(RepositoryEnv(backend_env_path))
    else:
        from decouple import config as env_config
    
    # Get configuration from environment
    github_token = env_config('GITHUB_TOKEN', default='')
    conductor_server = env_config('ORKES_SERVER_URL', default='http://localhost:8080/api')
    conductor_key = env_config('ORKES_API_KEY', default='')
    
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable is required")
        exit(1)
    
    # Create and start the agent
    agent = ReadmeUpdaterAgent(
        github_token=github_token,
        conductor_server_url=conductor_server,
        conductor_key=conductor_key
    )
    
    logger.info("Starting README Updater Agent...")
    agent.start_polling()