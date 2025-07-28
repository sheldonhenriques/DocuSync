import os
import json
import logging
from typing import Dict, Any, List
from conductor.client.worker.worker_task import worker_task
from conductor.client.configuration.configuration import Configuration
from conductor.client.configuration.settings.authentication_settings import AuthenticationSettings
from conductor.client.automator.task_handler import TaskHandler
from decouple import Config, RepositoryEnv

from github_client import GitHubClient


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CommitWatcherAgent:
    """
    Commit Watcher Agent that analyzes GitHub PR webhooks and identifies 
    documentation-relevant changes using the Conductor Python SDK.
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
        logger.info("Registering Commit Watcher Agent tasks...")
        
        # Tasks are automatically registered via @worker_task decorator
        # No manual registration needed with TaskHandler
    
    def start_polling(self):
        """Start polling for tasks from Conductor."""
        logger.info("Starting Commit Watcher Agent polling...")
        self.task_handler.start_processes()
    
    @worker_task(task_definition_name='analyze_pr_webhook')
    def analyze_pr_webhook(self, webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main task to analyze PR webhook payload and determine documentation impact.
        
        Args:
            webhook_payload: GitHub webhook payload for pull_request event
            
        Returns:
            Analysis results with documentation recommendations
        """
        try:
            logger.info(f"Processing PR webhook: {webhook_payload.get('action', 'unknown')}")
            
            # Extract PR information from webhook
            pr_info = self._extract_pr_info_from_webhook(webhook_payload)
            if not pr_info:
                return {"error": "Invalid webhook payload", "requires_documentation": False}
            
            # Get detailed PR analysis
            pr_analysis = self.github_client.analyze_pr_changes(
                owner=pr_info["owner"],
                repo=pr_info["repo"],
                pr_number=pr_info["pr_number"]
            )
            
            if "error" in pr_analysis:
                return {"error": pr_analysis["error"], "requires_documentation": False}
            
            # Determine documentation requirements
            doc_requirements = self._determine_documentation_requirements(pr_analysis)
            
            # Calculate priority level
            priority = self._calculate_priority(pr_analysis, doc_requirements)
            
            result = {
                "webhook_action": webhook_payload.get("action"),
                "repository": f"{pr_info['owner']}/{pr_info['repo']}",
                "pr_number": pr_info["pr_number"],
                "pr_title": pr_analysis["pr_details"]["title"],
                "pr_author": pr_analysis["pr_details"]["author"],
                "changes_summary": {
                    "files_changed": pr_analysis["pr_details"]["changed_files"],
                    "additions": pr_analysis["pr_details"]["additions"],
                    "deletions": pr_analysis["pr_details"]["deletions"],
                    "file_types": pr_analysis["file_analysis"]["file_types"]
                },
                "documentation_requirements": doc_requirements,
                "priority": priority,
                "requires_documentation": doc_requirements["requires_update"],
                "diff_preview": pr_analysis["diff"][:1000] if pr_analysis["diff"] else None,  # First 1000 chars
                "files_requiring_docs": self._identify_files_requiring_docs(pr_analysis["files"]),
                "suggested_actions": doc_requirements["suggested_actions"],
                "confidence_score": doc_requirements["confidence_score"]
            }
            
            logger.info(f"PR analysis completed. Requires docs: {result['requires_documentation']}")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing PR webhook: {e}")
            return {
                "error": str(e),
                "requires_documentation": False,
                "webhook_action": webhook_payload.get("action", "unknown")
            }
    
    @worker_task(task_definition_name='extract_pr_changes')
    def extract_pr_changes(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and categorize changes from PR data.
        
        Args:
            pr_data: PR analysis data
            
        Returns:
            Categorized changes summary
        """
        try:
            files = pr_data.get("files", [])
            
            changes = {
                "api_changes": [],
                "config_changes": [],
                "documentation_changes": [],
                "test_changes": [],
                "other_changes": []
            }
            
            for file in files:
                filename = file.get("filename", "")
                patch = file.get("patch", "")
                
                # Categorize based on filename and content
                if self._is_api_file(filename, patch):
                    changes["api_changes"].append({
                        "file": filename,
                        "type": "api",
                        "additions": file.get("additions", 0),
                        "deletions": file.get("deletions", 0)
                    })
                elif filename.endswith(('.json', '.yaml', '.yml', '.toml', '.ini')):
                    changes["config_changes"].append({
                        "file": filename,
                        "type": "config",
                        "additions": file.get("additions", 0),
                        "deletions": file.get("deletions", 0)
                    })
                elif filename.endswith(('.md', '.rst', '.txt')):
                    changes["documentation_changes"].append({
                        "file": filename,
                        "type": "documentation",
                        "additions": file.get("additions", 0),
                        "deletions": file.get("deletions", 0)
                    })
                elif 'test' in filename.lower():
                    changes["test_changes"].append({
                        "file": filename,
                        "type": "test",
                        "additions": file.get("additions", 0),
                        "deletions": file.get("deletions", 0)
                    })
                else:
                    changes["other_changes"].append({
                        "file": filename,
                        "type": "other",
                        "additions": file.get("additions", 0),
                        "deletions": file.get("deletions", 0)
                    })
            
            return changes
            
        except Exception as e:
            logger.error(f"Error extracting PR changes: {e}")
            return {"error": str(e)}
    
    @worker_task(task_definition_name='assess_documentation_priority')
    def assess_documentation_priority(self, changes_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the priority level for documentation updates based on changes.
        
        Args:
            changes_data: Categorized changes data
            
        Returns:
            Priority assessment with reasoning
        """
        try:
            priority_score = 0
            reasons = []
            
            # API changes have highest priority
            if changes_data.get("api_changes"):
                priority_score += 50
                reasons.append(f"API changes detected in {len(changes_data['api_changes'])} files")
            
            # Configuration changes have medium-high priority
            if changes_data.get("config_changes"):
                priority_score += 30
                reasons.append(f"Configuration changes in {len(changes_data['config_changes'])} files")
            
            # Documentation changes have medium priority (might need review)
            if changes_data.get("documentation_changes"):
                priority_score += 20
                reasons.append(f"Documentation files modified: {len(changes_data['documentation_changes'])}")
            
            # Test changes might indicate new features requiring docs
            if changes_data.get("test_changes"):
                priority_score += 15
                reasons.append(f"Test files changed: {len(changes_data['test_changes'])}")
            
            # Determine priority level
            if priority_score >= 50:
                priority = "high"
            elif priority_score >= 30:
                priority = "medium"
            elif priority_score >= 15:
                priority = "low"
            else:
                priority = "minimal"
            
            return {
                "priority": priority,
                "score": priority_score,
                "reasons": reasons,
                "recommendation": self._get_priority_recommendation(priority)
            }
            
        except Exception as e:
            logger.error(f"Error assessing documentation priority: {e}")
            return {"error": str(e), "priority": "unknown"}
    
    def _extract_pr_info_from_webhook(self, webhook_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract PR information from GitHub webhook payload."""
        try:
            pr = webhook_payload.get("pull_request", {})
            repo = webhook_payload.get("repository", {})
            
            return {
                "owner": repo.get("owner", {}).get("login"),
                "repo": repo.get("name"),
                "pr_number": pr.get("number"),
                "action": webhook_payload.get("action")
            }
        except Exception as e:
            logger.error(f"Error extracting PR info from webhook: {e}")
            return None
    
    def _determine_documentation_requirements(self, pr_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine if and what kind of documentation updates are required."""
        doc_impact = pr_analysis.get("documentation_impact", {})
        file_analysis = pr_analysis.get("file_analysis", {})
        
        requires_update = doc_impact.get("requires_doc_update", False)
        confidence_score = 0.5  # Base confidence
        
        suggested_actions = []
        
        # Check for API changes
        if any(f.endswith(('.py', '.js', '.ts', '.java')) for f in file_analysis.get("code_files", [])):
            confidence_score += 0.3
            suggested_actions.append("Review code changes for API documentation updates")
        
        # Check for configuration changes
        if file_analysis.get("config_files"):
            confidence_score += 0.2
            suggested_actions.append("Update configuration documentation")
        
        # Existing documentation changes
        if file_analysis.get("documentation_files"):
            confidence_score += 0.1
            suggested_actions.append("Review documentation changes for consistency")
        
        return {
            "requires_update": requires_update or confidence_score > 0.6,
            "confidence_score": min(confidence_score, 1.0),
            "impact_level": doc_impact.get("impact_level", "low"),
            "reasons": doc_impact.get("reasons", []),
            "suggested_actions": suggested_actions or doc_impact.get("suggested_actions", [])
        }
    
    def _calculate_priority(self, pr_analysis: Dict[str, Any], doc_requirements: Dict[str, Any]) -> str:
        """Calculate overall priority for documentation updates."""
        if not doc_requirements.get("requires_update", False):
            return "none"
        
        impact_level = doc_requirements.get("impact_level", "low")
        confidence = doc_requirements.get("confidence_score", 0.0)
        
        if impact_level == "high" and confidence > 0.8:
            return "critical"
        elif impact_level == "high" or confidence > 0.7:
            return "high"
        elif impact_level == "medium" or confidence > 0.5:
            return "medium"
        else:
            return "low"
    
    def _identify_files_requiring_docs(self, files: List[Dict[str, Any]]) -> List[str]:
        """Identify specific files that likely require documentation updates."""
        doc_files = []
        
        for file in files:
            filename = file.get("filename", "")
            patch = file.get("patch", "")
            
            # Check for API-related files
            if self._is_api_file(filename, patch):
                doc_files.append(filename)
            # Check for public interface changes
            elif "public" in patch.lower() or "export" in patch.lower():
                doc_files.append(filename)
        
        return doc_files
    
    def _is_api_file(self, filename: str, patch: str) -> bool:
        """Determine if a file contains API definitions."""
        api_indicators = [
            "api", "endpoint", "route", "controller", "service",
            "def ", "function ", "class ", "interface ", "@app.route",
            "router.", "express.", "fastapi"
        ]
        
        return (
            any(indicator in filename.lower() for indicator in api_indicators[:5]) or
            any(indicator in patch.lower() for indicator in api_indicators[5:])
        )
    
    def _get_priority_recommendation(self, priority: str) -> str:
        """Get recommendation based on priority level."""
        recommendations = {
            "high": "Immediate documentation review and update required",
            "medium": "Documentation review recommended within 24 hours",
            "low": "Documentation review can be scheduled for next sprint",
            "minimal": "Optional documentation review"
        }
        return recommendations.get(priority, "No specific recommendation")


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
    agent = CommitWatcherAgent(
        github_token=github_token,
        conductor_server_url=conductor_server,
        conductor_key=conductor_key
    )
    
    logger.info("Starting Commit Watcher Agent...")
    agent.start_polling()