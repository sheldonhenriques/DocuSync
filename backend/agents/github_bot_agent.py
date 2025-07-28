import os
import json
import logging
from typing import Dict, Any
from conductor.client.worker.worker_task import worker_task
from conductor.client.configuration.configuration import Configuration
from conductor.client.configuration.settings.authentication_settings import AuthenticationSettings
from conductor.client.automator.task_handler import TaskHandler
from decouple import Config, RepositoryEnv

from github_client import GitHubClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GitHubBotAgent:
    """
    GitHub Bot Agent that posts AI-generated summaries and documentation 
    suggestions as comments on pull requests.
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
        logger.info("Registering GitHub Bot Agent tasks...")
        # Tasks are automatically registered via @worker_task decorator
    
    def start_polling(self):
        """Start polling for tasks from Conductor."""
        logger.info("Starting GitHub Bot Agent polling...")
        self.task_handler.start_processes()
    
    @worker_task(task_definition_name='post_github_comment')
    def post_github_comment(self, pr_analysis: Dict[str, Any], ai_summary: Dict[str, Any] = None, 
                           ai_comment: Dict[str, Any] = None, documentation_result: Dict[str, Any] = None,
                           documentation_suggestions: Dict[str, Any] = None,
                           webhook_payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Post a comprehensive comment on the GitHub PR with AI-generated summaries 
        and documentation suggestions.
        
        Args:
            pr_analysis: Analysis results from the commit watcher
            ai_summary: AI-generated summary from Gemini (optional)
            ai_comment: AI-generated PR comment from Gemini (preferred)
            documentation_result: Documentation requirements assessment (optional)
            documentation_suggestions: AI-generated documentation suggestions (optional)
            webhook_payload: Original GitHub webhook payload (optional)
            
        Returns:
            Result of the comment posting operation
        """
        try:
            logger.info(f"Posting GitHub comment for PR #{pr_analysis.get('pr_number', 'unknown')}")
            
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
            
            # Generate the comment content using AI comment if available, otherwise build from components
            if ai_comment:
                # Use the AI-generated comment directly
                comment_body = self._extract_llm_output(ai_comment)
                if not comment_body:
                    # Fallback to building comment from components
                    comment_body = self._generate_comment_body(
                        pr_analysis=pr_analysis,
                        ai_summary=ai_summary,
                        documentation_result=documentation_result,
                        documentation_suggestions=documentation_suggestions
                    )
            else:
                # Build comment from individual components
                comment_body = self._generate_comment_body(
                    pr_analysis=pr_analysis,
                    ai_summary=ai_summary,
                    documentation_result=documentation_result,
                    documentation_suggestions=documentation_suggestions
                )
            
            # Post the comment using GitHub API
            success = self._post_pr_comment(owner, repo, pr_number, comment_body)
            
            if success:
                logger.info(f"Successfully posted comment on PR #{pr_number}")
                return {
                    "status": "success",
                    "message": f"Comment posted on {repo_full_name}#{pr_number}",
                    "comment_length": len(comment_body)
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to post comment to GitHub"
                }
                
        except Exception as e:
            logger.error(f"Error posting GitHub comment: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    @worker_task(task_definition_name='skip_documentation_task')
    def skip_documentation_task(self, reason: str, pr_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle the case where documentation updates are not required.
        
        Args:
            reason: Reason for skipping documentation
            pr_analysis: PR analysis results
            
        Returns:
            Skip operation result
        """
        try:
            logger.info(f"Skipping documentation for PR #{pr_analysis.get('pr_number', 'unknown')}: {reason}")
            
            return {
                "status": "skipped",
                "reason": reason,
                "pr_number": pr_analysis.get('pr_number'),
                "repository": pr_analysis.get('repository'),
                "requires_documentation": False
            }
            
        except Exception as e:
            logger.error(f"Error in skip documentation task: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _generate_comment_body(self, pr_analysis: Dict[str, Any], ai_summary: Dict[str, Any], 
                              documentation_result: Dict[str, Any], documentation_suggestions: Dict[str, Any] = None) -> str:
        """Generate the GitHub comment body with AI summaries and documentation suggestions."""
        
        # Extract AI summary text
        ai_summary_text = self._extract_llm_output(ai_summary)
        doc_suggestions_text = self._extract_llm_output(documentation_suggestions) if documentation_suggestions else None
        
        # Build comment body
        comment_parts = [
            "## 🤖 DocuSync AI Analysis",
            "",
            "### 📊 Change Summary",
            ai_summary_text if ai_summary_text else "AI summary generation failed or not available.",
            "",
            f"### 📋 Analysis Details",
            f"- **Priority**: {pr_analysis.get('priority', 'unknown')}",
            f"- **Files Changed**: {pr_analysis.get('changes_summary', {}).get('files_changed', 0)}",
            f"- **Additions**: +{pr_analysis.get('changes_summary', {}).get('additions', 0)}",
            f"- **Deletions**: -{pr_analysis.get('changes_summary', {}).get('deletions', 0)}",
            f"- **Confidence Score**: {pr_analysis.get('confidence_score', 'N/A')}",
            ""
        ]
        
        # Add documentation section
        requires_docs = pr_analysis.get('requires_documentation', False)
        if requires_docs and doc_suggestions_text:
            comment_parts.extend([
                "### 📚 Documentation Updates Required",
                doc_suggestions_text,
                ""
            ])
        elif requires_docs:
            comment_parts.extend([
                "### 📚 Documentation Updates Required",
                "This PR requires documentation updates. Please review the suggested actions below:",
                ""
            ])
            
            # Add suggested actions if available
            suggested_actions = pr_analysis.get('suggested_actions', [])
            if suggested_actions:
                comment_parts.append("**Suggested Actions:**")
                for action in suggested_actions:
                    comment_parts.append(f"- {action}")
                comment_parts.append("")
        else:
            comment_parts.extend([
                "### ✅ No Documentation Updates Required",
                "This PR does not require documentation updates based on the automated analysis.",
                ""
            ])
        
        # Add footer
        comment_parts.extend([
            "---",
            "*This analysis was generated automatically by DocuSync AI. For questions or feedback, please contact the documentation team.*"
        ])
        
        return "\n".join(comment_parts)
    
    def _extract_llm_output(self, llm_result: Dict[str, Any]) -> str:
        """Extract the generated text from LLM task output."""
        if not llm_result:
            return None
            
        logger.info(f"Extracting LLM output from: {type(llm_result)}")
        logger.debug(f"LLM result keys: {list(llm_result.keys()) if isinstance(llm_result, dict) else 'Not a dict'}")
        
        # Handle different LLM response formats
        if isinstance(llm_result, str):
            return llm_result
        
        if isinstance(llm_result, dict):
            # Try different possible keys in order of preference
            possible_keys = [
                'output',           # Orkes LLM task standard output
                'result',           # Common result key
                'text',             # Direct text response
                'response',         # Generic response
                'generated_text',   # Hugging Face style
                'content',          # OpenAPI style
                'message',          # Message format
                'data'              # Generic data field
            ]
            
            for key in possible_keys:
                if key in llm_result and llm_result[key]:
                    value = llm_result[key]
                    logger.info(f"Found LLM output in key '{key}': {type(value)}")
                    
                    # Handle nested structures
                    if isinstance(value, dict):
                        # Try to extract from nested dict
                        nested_keys = ['text', 'content', 'message', 'output']
                        for nested_key in nested_keys:
                            if nested_key in value and value[nested_key]:
                                logger.info(f"Found nested LLM output in '{key}.{nested_key}'")
                                return str(value[nested_key])
                        # If no nested key found, stringify the whole nested dict
                        return str(value)
                    
                    return str(value)
        
        # Last resort: stringify the entire result
        logger.warning(f"Could not extract LLM output, using full result: {llm_result}")
        return str(llm_result) if llm_result else "AI response could not be processed."
    
    def _post_pr_comment(self, owner: str, repo: str, pr_number: int, comment_body: str) -> bool:
        """Post a comment to the GitHub PR."""
        try:
            import requests
            
            if not self.github_token:
                logger.error("GitHub token not available for posting comment")
                return False
            
            url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "DocuSync-Bot"
            }
            
            # Add footer to indicate this is an AI-generated comment
            final_comment_body = comment_body + "\n\n---\n*🤖 This comment was generated by DocuSync AI using Google Gemini*"
            
            data = {
                "body": final_comment_body
            }
            
            logger.info(f"Posting comment to {owner}/{repo}#{pr_number}")
            logger.debug(f"Comment length: {len(final_comment_body)} characters")
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            response_data = response.json()
            comment_url = response_data.get('html_url', 'Unknown')
            
            logger.info(f"✅ Comment posted successfully!")
            logger.info(f"   Status: {response.status_code}")
            logger.info(f"   Comment ID: {response_data.get('id', 'Unknown')}")
            logger.info(f"   URL: {comment_url}")
            
            return True
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP error posting GitHub comment: {e}")
            logger.error(f"   Response: {e.response.text if e.response else 'No response'}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to post GitHub comment: {e}")
            return False


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
    agent = GitHubBotAgent(
        github_token=github_token,
        conductor_server_url=conductor_server,
        conductor_key=conductor_key
    )
    
    logger.info("Starting GitHub Bot Agent...")
    agent.start_polling()